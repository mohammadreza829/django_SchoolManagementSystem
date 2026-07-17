"""چرخهٔ عمر تلاش آزمون و ثبت پاسخ‌ها را به‌صورت تراکنشی مدیریت می‌کند."""

from django.db import IntegrityError, transaction

from .models import AttemptAnswer, Choice, Question, QuizAttempt


class QuizServiceError(Exception):
    """خطای قابل نمایش مربوط به شروع یا ثبت آزمون است."""


def attempts_exhausted(*, quiz, user):
    """بررسی می‌کند تعداد تلاش‌های تکمیل‌شده به سقف آزمون رسیده است یا نه."""
    if quiz.max_attempts <= 0:
        return False
    completed_count = QuizAttempt.objects.filter(
        quiz=quiz,
        student=user,
        status=QuizAttempt.COMPLETED,
    ).count()
    return completed_count >= quiz.max_attempts


def get_or_create_open_attempt(*, quiz, user):
    """یک تلاش باز یکتا می‌گیرد یا با اتکا به constraint دیتابیس ایجاد می‌کند."""
    with transaction.atomic():
        if attempts_exhausted(quiz=quiz, user=user):
            raise QuizServiceError(
                "شما به حداکثر دفعات مجاز برای این آزمون رسیده‌اید."
            )
        try:
            attempt, _created = QuizAttempt.objects.get_or_create(
                quiz=quiz,
                student=user,
                status=QuizAttempt.IN_PROGRESS,
                defaults={"max_score": quiz.total_points},
            )
        except IntegrityError:
            # درخواست هم‌زمان دیگر رکورد را ساخته است؛ همان رکورد یکتا خوانده می‌شود.
            attempt = QuizAttempt.objects.get(
                quiz=quiz,
                student=user,
                status=QuizAttempt.IN_PROGRESS,
            )
    return attempt


def finalize_attempt(*, attempt, post_data, questions):
    """پاسخ‌ها را idempotent ذخیره، تصحیح و تلاش قفل‌شده را نهایی می‌کند."""
    with transaction.atomic():
        locked_attempt = QuizAttempt.objects.select_for_update().select_related(
            "quiz"
        ).get(pk=attempt.pk)
        if locked_attempt.status == QuizAttempt.COMPLETED:
            return locked_attempt

        for question in questions:
            answer, _created = AttemptAnswer.objects.get_or_create(
                attempt=locked_attempt,
                question=question,
            )
            _apply_submitted_answer(
                answer=answer,
                question=question,
                post_data=post_data,
            )
            answer.grade()

        locked_attempt.calculate_score()
    return locked_attempt


def _apply_submitted_answer(*, answer, question, post_data):
    """مقدار ارسال‌شده را متناسب با نوع سؤال روی پاسخ اعمال می‌کند."""
    if post_data is None:
        return

    field_name = f"question_{question.id}"
    if question.question_type in (Question.SINGLE, Question.TRUE_FALSE):
        choice_id = post_data.get(field_name)
        selected_choices = Choice.objects.filter(
            id=choice_id,
            question=question,
        ) if choice_id else Choice.objects.none()
        answer.selected_choices.set(selected_choices)
    elif question.question_type == Question.MULTIPLE:
        choice_ids = post_data.getlist(field_name)
        answer.selected_choices.set(
            Choice.objects.filter(id__in=choice_ids, question=question)
        )
    else:
        answer.answer_text = (post_data.get(field_name) or "").strip()
        answer.save(update_fields=("answer_text",))


def sweep_expired_attempts(user):
    """تلاش‌های باز منقضی‌شدهٔ کاربر را بدون وابستگی به view نهایی می‌کند."""
    if not user.is_authenticated:
        return
    open_attempts = QuizAttempt.objects.filter(
        student=user,
        status=QuizAttempt.IN_PROGRESS,
    ).select_related("quiz")
    for attempt in open_attempts:
        if attempt.is_expired:
            finalize_attempt(
                attempt=attempt,
                post_data=None,
                questions=attempt.quiz.get_questions(),
            )
