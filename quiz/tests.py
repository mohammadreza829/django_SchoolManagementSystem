"""تست‌های دامنهٔ آزمون.

تمرکز روی `services.py` و تصحیح خودکار است: تلاش باز یکتا، سقف تلاش،
idempotent بودن ثبت نهایی و درستی نمره‌دهی برای همهٔ انواع سوال.
"""

from datetime import timedelta
from itertools import count

from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.test import TestCase
from django.utils import timezone

from .models import AttemptAnswer, Choice, Question, Quiz, QuizAttempt, QuizQuestion, Topic
from .services import (
    QuizServiceError,
    attempts_exhausted,
    finalize_attempt,
    get_or_create_open_attempt,
    sweep_expired_attempts,
)

User = get_user_model()

TEST_PASSWORD = "test-pass-12345"

_national_code_sequence = count(2000000000)


def create_user(username, role="student"):
    """یک کاربر تست با کد ملی و ایمیل یکتا می‌سازد."""
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=TEST_PASSWORD,
        national_code=str(next(_national_code_sequence)),
        role=role,
    )


def build_post_data(values):
    """یک QueryDict شبیه request.POST می‌سازد (چون سرویس از getlist استفاده می‌کند)."""
    post_data = QueryDict(mutable=True)
    for field_name, value in values.items():
        if isinstance(value, (list, tuple, set)):
            post_data.setlist(field_name, [str(item) for item in value])
        else:
            post_data[field_name] = str(value)
    return post_data


class QuizTestMixin:
    """ابزارهای مشترک ساخت آزمون و سوال برای تست‌ها."""

    def create_quiz(self, title="آزمون تست", **extra_fields):
        """یک آزمون منتشرشده می‌سازد (slug خودکار)."""
        return Quiz.objects.create(title=title, is_published=True, **extra_fields)

    def add_question(self, quiz, *, question_type=Question.SINGLE, order=1, **extra_fields):
        """یک سوال می‌سازد و آن را به آزمون وصل می‌کند."""
        question = Question.objects.create(
            topic=self.topic,
            text=f"متن سوال {order}",
            question_type=question_type,
            **extra_fields,
        )
        QuizQuestion.objects.create(quiz=quiz, question=question, order=order)
        return question

    def add_choices(self, question, correct_indexes, total=3):
        """برای سوال گزینه‌محور، گزینه‌ها را می‌سازد و لیستشان را برمی‌گرداند."""
        return [
            Choice.objects.create(
                question=question,
                text=f"گزینهٔ {index}",
                is_correct=index in correct_indexes,
                order=index,
            )
            for index in range(total)
        ]


# ==============================================================
#  چرخهٔ عمر تلاش
# ==============================================================
class QuizAttemptLifecycleTests(QuizTestMixin, TestCase):
    """ساخت تلاش باز، یکتایی آن و سقف تعداد تلاش."""

    def setUp(self):
        self.student = create_user("quiz_student")
        self.topic = Topic.objects.create(name="ریاضی")
        self.quiz = self.create_quiz()
        self.question = self.add_question(self.quiz, points=2)
        self.choices = self.add_choices(self.question, correct_indexes={0})

    def test_second_call_returns_the_same_open_attempt(self):
        """دو بار باز کردن آزمون نباید دو تلاش بسازد."""
        first = get_or_create_open_attempt(quiz=self.quiz, user=self.student)
        second = get_or_create_open_attempt(quiz=self.quiz, user=self.student)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(QuizAttempt.objects.count(), 1)
        self.assertEqual(first.status, QuizAttempt.IN_PROGRESS)
        self.assertEqual(first.max_score, self.quiz.total_points)

    def test_unlimited_attempts_by_default(self):
        self.assertFalse(attempts_exhausted(quiz=self.quiz, user=self.student))

    def test_attempt_limit_is_enforced(self):
        limited_quiz = self.create_quiz("آزمون یک‌باره", max_attempts=1)
        question = self.add_question(limited_quiz)
        self.add_choices(question, correct_indexes={0})

        attempt = get_or_create_open_attempt(quiz=limited_quiz, user=self.student)
        finalize_attempt(
            attempt=attempt,
            post_data=None,
            questions=limited_quiz.get_questions(),
        )

        self.assertTrue(attempts_exhausted(quiz=limited_quiz, user=self.student))
        with self.assertRaises(QuizServiceError):
            get_or_create_open_attempt(quiz=limited_quiz, user=self.student)

    def test_different_students_have_separate_attempts(self):
        other_student = create_user("quiz_student_2")

        first = get_or_create_open_attempt(quiz=self.quiz, user=self.student)
        second = get_or_create_open_attempt(quiz=self.quiz, user=other_student)

        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(QuizAttempt.objects.count(), 2)


# ==============================================================
#  ثبت نهایی و تصحیح
# ==============================================================
class FinalizeAttemptTests(QuizTestMixin, TestCase):
    """نمره‌دهی، درصد، قبولی و idempotency ثبت نهایی."""

    def setUp(self):
        self.student = create_user("quiz_finalize")
        self.topic = Topic.objects.create(name="فیزیک")
        self.quiz = self.create_quiz(pass_mark=50)
        self.question = self.add_question(self.quiz, points=4)
        self.choices = self.add_choices(self.question, correct_indexes={0})
        self.attempt = get_or_create_open_attempt(quiz=self.quiz, user=self.student)

    def _finalize(self, values):
        return finalize_attempt(
            attempt=self.attempt,
            post_data=build_post_data(values),
            questions=self.quiz.get_questions(),
        )

    def test_correct_answer_gives_full_score(self):
        finalized = self._finalize(
            {f"question_{self.question.id}": self.choices[0].id}
        )

        self.assertEqual(finalized.status, QuizAttempt.COMPLETED)
        self.assertEqual(finalized.score, 4)
        self.assertEqual(finalized.max_score, 4)
        self.assertEqual(finalized.percentage, 100)
        self.assertTrue(finalized.is_passed)
        self.assertIsNotNone(finalized.completed_at)

    def test_wrong_answer_gives_zero_and_fails(self):
        finalized = self._finalize(
            {f"question_{self.question.id}": self.choices[1].id}
        )

        self.assertEqual(finalized.score, 0)
        self.assertEqual(finalized.percentage, 0)
        self.assertFalse(finalized.is_passed)

    def test_unanswered_question_gives_zero(self):
        finalized = finalize_attempt(
            attempt=self.attempt,
            post_data=None,
            questions=self.quiz.get_questions(),
        )

        self.assertEqual(finalized.score, 0)
        self.assertFalse(finalized.is_passed)
        self.assertEqual(AttemptAnswer.objects.count(), 1)

    def test_finalize_is_idempotent(self):
        """ارسال دوبارهٔ فرم (رفرش صفحه) نباید نمره را عوض کند."""
        first = self._finalize({f"question_{self.question.id}": self.choices[0].id})
        first_score = first.score

        second = self._finalize({f"question_{self.question.id}": self.choices[1].id})

        self.assertEqual(second.score, first_score)
        self.assertEqual(second.percentage, 100)
        self.assertEqual(AttemptAnswer.objects.count(), 1)

    def test_pass_mark_boundary_is_inclusive(self):
        """دقیقاً روی حد نصاب باید قبول حساب شود."""
        boundary_quiz = self.create_quiz("آزمون حد نصاب", pass_mark=50)
        first_question = self.add_question(boundary_quiz, order=1, points=1)
        self.add_choices(first_question, correct_indexes={0})
        second_question = self.add_question(boundary_quiz, order=2, points=1)
        self.add_choices(second_question, correct_indexes={0})

        attempt = get_or_create_open_attempt(quiz=boundary_quiz, user=self.student)
        correct_choice = first_question.choices.filter(is_correct=True).first()
        finalized = finalize_attempt(
            attempt=attempt,
            post_data=build_post_data(
                {f"question_{first_question.id}": correct_choice.id}
            ),
            questions=boundary_quiz.get_questions(),
        )

        self.assertEqual(finalized.percentage, 50)
        self.assertTrue(finalized.is_passed)


# ==============================================================
#  تصحیح انواع سوال
# ==============================================================
class GradingByQuestionTypeTests(QuizTestMixin, TestCase):
    """درستی تصحیح خودکار برای چندگزینه‌ای، عددی و پاسخ کوتاه."""

    def setUp(self):
        self.student = create_user("quiz_grading")
        self.topic = Topic.objects.create(name="شیمی")

    def _run(self, quiz, values):
        attempt = get_or_create_open_attempt(quiz=quiz, user=self.student)
        return finalize_attempt(
            attempt=attempt,
            post_data=build_post_data(values),
            questions=quiz.get_questions(),
        )

    def test_multiple_choice_requires_the_exact_set(self):
        quiz = self.create_quiz("آزمون چندگزینه‌ای")
        question = self.add_question(quiz, question_type=Question.MULTIPLE)
        choices = self.add_choices(question, correct_indexes={0, 1})

        partial = self._run(quiz, {f"question_{question.id}": [choices[0].id]})
        self.assertEqual(partial.score, 0)

        # تلاش دوم با پاسخ کامل
        complete = self._run(
            quiz, {f"question_{question.id}": [choices[0].id, choices[1].id]}
        )
        self.assertEqual(complete.percentage, 100)

    def test_numeric_answer_respects_tolerance(self):
        quiz = self.create_quiz("آزمون عددی")
        question = self.add_question(
            quiz,
            question_type=Question.NUMERIC,
            correct_numeric=2.5,
            numeric_tolerance=0.1,
        )

        within_tolerance = self._run(quiz, {f"question_{question.id}": "2.55"})
        self.assertEqual(within_tolerance.percentage, 100)

        outside_tolerance = self._run(quiz, {f"question_{question.id}": "3"})
        self.assertEqual(outside_tolerance.percentage, 0)

    def test_non_numeric_input_is_not_a_crash(self):
        """ورودی نامعتبر باید غلط حساب شود، نه اینکه ValueError بدهد."""
        quiz = self.create_quiz("آزمون عددی نامعتبر")
        question = self.add_question(
            quiz, question_type=Question.NUMERIC, correct_numeric=1.0
        )

        finalized = self._run(quiz, {f"question_{question.id}": "عدد نیست"})

        self.assertEqual(finalized.percentage, 0)

    def test_short_answer_ignores_case_and_spaces(self):
        quiz = self.create_quiz("آزمون پاسخ کوتاه")
        question = self.add_question(
            quiz, question_type=Question.SHORT, correct_text="Django"
        )

        finalized = self._run(quiz, {f"question_{question.id}": "  django "})

        self.assertEqual(finalized.percentage, 100)


# ==============================================================
#  انقضای زمانی
# ==============================================================
class ExpiredAttemptTests(QuizTestMixin, TestCase):
    """تلاش‌های باز که زمانشان تمام شده باید خودکار نهایی شوند."""

    def setUp(self):
        self.student = create_user("quiz_expiry")
        self.topic = Topic.objects.create(name="زیست")
        self.quiz = self.create_quiz("آزمون زمان‌دار", time_limit_minutes=10)
        question = self.add_question(self.quiz)
        self.add_choices(question, correct_indexes={0})

    def test_expired_open_attempt_is_finalized_by_sweep(self):
        attempt = get_or_create_open_attempt(quiz=self.quiz, user=self.student)
        # started_at با auto_now_add ست می‌شود، پس با update عقب می‌بریمش
        QuizAttempt.objects.filter(pk=attempt.pk).update(
            started_at=timezone.now() - timedelta(minutes=30)
        )
        attempt.refresh_from_db()
        self.assertTrue(attempt.is_expired)

        sweep_expired_attempts(self.student)

        attempt.refresh_from_db()
        self.assertEqual(attempt.status, QuizAttempt.COMPLETED)

    def test_fresh_attempt_is_not_touched_by_sweep(self):
        attempt = get_or_create_open_attempt(quiz=self.quiz, user=self.student)

        sweep_expired_attempts(self.student)

        attempt.refresh_from_db()
        self.assertEqual(attempt.status, QuizAttempt.IN_PROGRESS)
        self.assertIsNotNone(attempt.remaining_seconds)
