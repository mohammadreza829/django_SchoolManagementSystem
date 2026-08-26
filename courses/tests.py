"""تست‌های دامنهٔ دوره.

تمرکز این تست‌ها روی قواعد کسب‌وکار (`services.py`) است، نه جزئیات نمایش؛
چون منطق ظرفیت، پرداخت و پیشرفت همان چیزی است که اگر بشکند، داده خراب می‌شود.
چند تست ویو هم برای «رگرسیون» باگ‌های رفع‌شده نوشته شده تا دوباره برنگردند.
"""

from datetime import timedelta
from itertools import count

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from Enrollment.models import Enrollment

from .models import Course, CourseRating, Lesson, LessonProgress
from .services import (
    CourseServiceError,
    add_lesson_comment,
    enroll_student,
    mark_lesson_completed,
    set_course_rating,
)

User = get_user_model()

TEST_PASSWORD = "test-pass-12345"

# کد ملی در مدل User یکتا و اجباری است، پس برای هر کاربر تست یک مقدار تازه لازم داریم.
_national_code_sequence = count(1000000000)


def create_user(username, role="student", **extra_fields):
    """یک کاربر تست با کد ملی و ایمیل یکتا می‌سازد."""
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=TEST_PASSWORD,
        national_code=str(next(_national_code_sequence)),
        role=role,
        **extra_fields,
    )


def create_course(title="دورهٔ تست", *, price=0, status="published", **extra_fields):
    """یک دورهٔ منتشرشدهٔ رایگان می‌سازد (slug خودکار تولید می‌شود)."""
    return Course.objects.create(
        title=title,
        description="توضیحات کامل دورهٔ تست",
        short_description="توضیح کوتاه دورهٔ تست",
        price=price,
        status=status,
        **extra_fields,
    )


def create_lesson(course, order=1, **extra_fields):
    """یک جلسه برای دورهٔ داده‌شده می‌سازد."""
    return Lesson.objects.create(
        course=course,
        title=f"جلسهٔ {order}",
        order=order,
        **extra_fields,
    )


# ==============================================================
#  ثبت‌نام
# ==============================================================
class EnrollStudentServiceTests(TestCase):
    """قواعد ثبت‌نام: ظرفیت، مهلت، تکرار، وضعیت پرداخت و همگام‌سازی آمار."""

    def setUp(self):
        self.student = create_user("student_enroll")
        self.course = create_course("دورهٔ رایگان")

    def test_free_course_enrollment_grants_access(self):
        result = enroll_student(student=self.student, course=self.course)

        self.assertTrue(result.created)
        self.assertTrue(result.access_granted)
        self.assertEqual(result.enrollment.status, "active")
        self.assertEqual(result.enrollment.payment_status, "free")

        self.course.refresh_from_db()
        self.assertEqual(self.course.enroll_count, 1)
        self.assertFalse(self.course.is_full)

    def test_paid_course_enrollment_stays_pending(self):
        """دورهٔ پولی تا پرداخت نشود نباید دسترسی بدهد."""
        paid_course = create_course("دورهٔ پولی", price=500000)

        result = enroll_student(student=self.student, course=paid_course)

        self.assertEqual(result.enrollment.payment_status, "pending")
        self.assertFalse(result.access_granted)

    def test_duplicate_enrollment_is_rejected(self):
        enroll_student(student=self.student, course=self.course)

        with self.assertRaises(CourseServiceError):
            enroll_student(student=self.student, course=self.course)

        self.assertEqual(Enrollment.objects.count(), 1)

    def test_cancelled_enrollment_can_be_reactivated(self):
        """ثبت‌نام لغوشده باید دوباره فعال شود، نه اینکه رکورد دوم بسازد."""
        first = enroll_student(student=self.student, course=self.course)
        Enrollment.objects.filter(pk=first.enrollment.pk).update(status="cancelled")

        result = enroll_student(student=self.student, course=self.course)

        self.assertFalse(result.created)
        self.assertEqual(result.enrollment.status, "active")
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_full_capacity_blocks_enrollment(self):
        limited_course = create_course("دورهٔ محدود", capacity=1)
        first_student = create_user("student_first")
        enroll_student(student=first_student, course=limited_course)

        limited_course.refresh_from_db()
        self.assertTrue(limited_course.is_full)
        self.assertEqual(limited_course.seats_left, 0)

        with self.assertRaises(CourseServiceError):
            enroll_student(student=self.student, course=limited_course)

    def test_cancelled_enrollment_frees_a_seat(self):
        """صندلی ثبت‌نام لغوشده باید آزاد شود (وگرنه ظرفیت اشتباه پر می‌ماند)."""
        limited_course = create_course("دورهٔ یک‌نفره", capacity=1)
        first_student = create_user("student_leaving")
        first = enroll_student(student=first_student, course=limited_course)
        Enrollment.objects.filter(pk=first.enrollment.pk).update(status="cancelled")

        result = enroll_student(student=self.student, course=limited_course)

        self.assertTrue(result.access_granted)

    def test_past_deadline_blocks_enrollment(self):
        expired_course = create_course(
            "دورهٔ منقضی",
            enrollment_deadline=timezone.now() - timedelta(days=1),
        )

        with self.assertRaises(CourseServiceError):
            enroll_student(student=self.student, course=expired_course)

    def test_unpublished_course_blocks_enrollment(self):
        draft_course = create_course("پیش‌نویس", status="draft")

        with self.assertRaises(CourseServiceError):
            enroll_student(student=self.student, course=draft_course)

    def test_enrollment_creates_notification(self):
        enroll_student(student=self.student, course=self.course)

        self.assertEqual(self.student.notifications.count(), 1)


# ==============================================================
#  پیشرفت جلسه
# ==============================================================
class MarkLessonCompletedServiceTests(TestCase):
    """تکمیل جلسه باید idempotent باشد."""

    def setUp(self):
        self.student = create_user("student_progress")
        self.course = create_course()
        self.lesson = create_lesson(self.course)

    def test_marking_twice_keeps_a_single_progress_row(self):
        mark_lesson_completed(user=self.student, lesson=self.lesson)
        progress = mark_lesson_completed(user=self.student, lesson=self.lesson)

        self.assertEqual(LessonProgress.objects.count(), 1)
        self.assertTrue(progress.is_completed)
        self.assertEqual(progress.completion_percentage, 100)
        self.assertIsNotNone(progress.completed_at)


# ==============================================================
#  امتیاز دوره
# ==============================================================
class CourseRatingServiceTests(TestCase):
    """ثبت امتیاز و همگام‌سازی میانگین دوره."""

    def setUp(self):
        self.student = create_user("student_rating")
        self.course = create_course()

    def test_valid_rating_updates_course_summary(self):
        _rating, created = set_course_rating(
            user=self.student, course=self.course, score=4
        )

        self.assertTrue(created)
        self.course.refresh_from_db()
        self.assertEqual(self.course.rating_count, 1)
        self.assertEqual(float(self.course.rating_avg), 4.0)

    def test_same_user_rating_twice_updates_instead_of_duplicating(self):
        set_course_rating(user=self.student, course=self.course, score=5)
        _rating, created = set_course_rating(
            user=self.student, course=self.course, score=2
        )

        self.assertFalse(created)
        self.assertEqual(CourseRating.objects.count(), 1)
        self.course.refresh_from_db()
        self.assertEqual(self.course.rating_count, 1)
        self.assertEqual(float(self.course.rating_avg), 2.0)

    def test_average_of_two_users(self):
        other_student = create_user("student_rating_2")
        set_course_rating(user=self.student, course=self.course, score=5)
        set_course_rating(user=other_student, course=self.course, score=2)

        self.course.refresh_from_db()
        self.assertEqual(self.course.rating_count, 2)
        self.assertEqual(float(self.course.rating_avg), 3.5)

    def test_out_of_range_and_invalid_scores_are_rejected(self):
        for invalid_score in (0, 6, "", None, "خیلی خوب"):
            with self.subTest(score=invalid_score):
                with self.assertRaises(CourseServiceError):
                    set_course_rating(
                        user=self.student, course=self.course, score=invalid_score
                    )


# ==============================================================
#  نظر جلسه
# ==============================================================
class AddLessonCommentServiceTests(TestCase):
    """ثبت نظر و همگام‌سازی شمارندهٔ نظرات."""

    def setUp(self):
        self.student = create_user("student_comment")
        self.course = create_course()
        self.lesson = create_lesson(self.course)

    def test_blank_comment_is_rejected(self):
        for blank_text in ("", "   ", "\n\t"):
            with self.subTest(text=repr(blank_text)):
                with self.assertRaises(CourseServiceError):
                    add_lesson_comment(
                        user=self.student, lesson=self.lesson, text=blank_text
                    )

    def test_valid_comment_updates_counter(self):
        comment = add_lesson_comment(
            user=self.student, lesson=self.lesson, text="  ممنون از توضیحات  "
        )

        self.assertEqual(comment.text, "ممنون از توضیحات")
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.comment_count, 1)


# ==============================================================
#  ویو «دوره‌های من» — تست رگرسیون باگ‌های رفع‌شده
# ==============================================================
class MyCoursesViewTests(TestCase):
    """رفتار صفحهٔ «دوره‌های من» پس از رفع N+1 و فیلتر وضعیت ثبت‌نام."""

    def setUp(self):
        self.student = create_user("student_my_courses")
        self.client.login(username=self.student.username, password=TEST_PASSWORD)
        self.url = reverse("courses:my_courses")

    def _enroll_in_course(self, title, lesson_count=0):
        course = create_course(title)
        for order in range(1, lesson_count + 1):
            create_lesson(course, order=order)
        enroll_student(student=self.student, course=course)
        return course

    def test_cancelled_enrollment_is_not_listed(self):
        """دوره‌ای که ثبت‌نامش لغو شده نباید در «دوره‌های من» بیاید."""
        active_course = self._enroll_in_course("دورهٔ فعال")
        cancelled_course = self._enroll_in_course("دورهٔ لغوشده")
        Enrollment.objects.filter(course=cancelled_course).update(status="cancelled")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        listed_ids = {course.id for course in response.context["courses"]}
        self.assertIn(active_course.id, listed_ids)
        self.assertNotIn(cancelled_course.id, listed_ids)

    def test_progress_percentage_is_annotated_correctly(self):
        """با ۲ جلسه که یکی تکمیل شده، پیشرفت باید ۵۰ درصد باشد."""
        course = self._enroll_in_course("دورهٔ دوجلسه‌ای", lesson_count=2)
        first_lesson = course.lessons.order_by("order").first()
        mark_lesson_completed(user=self.student, lesson=first_lesson)

        response = self.client.get(self.url)

        listed_course = response.context["courses"][0]
        self.assertEqual(listed_course.total_lessons_count, 2)
        self.assertEqual(listed_course.completed_lessons, 1)
        self.assertEqual(listed_course.progress_percentage, 50)

    def test_progress_is_zero_for_course_without_lessons(self):
        """دورهٔ بدون جلسه نباید باعث تقسیم بر صفر شود."""
        self._enroll_in_course("دورهٔ بدون جلسه")

        response = self.client.get(self.url)

        self.assertEqual(response.context["courses"][0].progress_percentage, 0)

    def test_query_count_does_not_grow_with_number_of_courses(self):
        """تست رگرسیون N+1: تعداد کوئری نباید با تعداد دوره‌ها زیاد شود."""
        self._enroll_in_course("دورهٔ اول", lesson_count=2)
        with CaptureQueriesContext(connection) as single_course_queries:
            self.client.get(self.url)

        for index in range(2, 6):
            self._enroll_in_course(f"دورهٔ {index}", lesson_count=2)
        with CaptureQueriesContext(connection) as many_courses_queries:
            self.client.get(self.url)

        # با N+1 قدیمی، ۵ دوره حدود ۸ کوئری بیشتر می‌زد.
        self.assertLessEqual(
            len(many_courses_queries),
            len(single_course_queries) + 2,
            "احتمالاً N+1 برگشته است: تعداد کوئری با تعداد دوره‌ها رشد کرد.",
        )


# ==============================================================
#  جست‌وجو — تست رگرسیون صفحه‌بندی
# ==============================================================
class SearchCoursesViewTests(TestCase):
    """صفحه‌بندی و شمارش نتایج جست‌وجو."""

    def setUp(self):
        self.url = reverse("courses:search")

    def test_empty_query_returns_no_results(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["count"], 0)

    def test_results_are_paginated(self):
        for index in range(1, 12):
            create_course(f"جنگو {index}")

        response = self.client.get(self.url, {"q": "جنگو"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["count"], 11)
        # COURSES_PER_PAGE = 9 → صفحهٔ اول باید ۹ آیتم داشته باشد
        self.assertEqual(len(response.context["courses"]), 9)
        self.assertTrue(response.context["is_paginated"])

    def test_draft_courses_are_not_searchable(self):
        create_course("دورهٔ پیش‌نویس جنگو", status="draft")

        response = self.client.get(self.url, {"q": "جنگو"})

        self.assertEqual(response.context["count"], 0)
