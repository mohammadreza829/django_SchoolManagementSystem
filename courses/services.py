"""کاربردهای اصلی دامنهٔ دوره را به‌صورت سرویس‌های تراکنشی پیاده‌سازی می‌کند.

Viewها فقط ورودی HTTP و پیام خروجی را مدیریت می‌کنند؛ قواعد ثبت‌نام، ظرفیت،
پیشرفت، نظر و امتیاز در این فایل متمرکز شده‌اند.
"""

from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import Avg
from django.utils import timezone

from accounts.models import Notification
from Enrollment.models import Enrollment

from .models import Course, CourseRating, LessonComment, LessonProgress


class CourseServiceError(Exception):
    """خطای قابل نمایش مربوط به یکی از عملیات دامنهٔ دوره است."""


@dataclass(frozen=True)
class EnrollmentResult:
    """نتیجهٔ ثبت‌نام را بدون وابستگی به HTTP به فراخواننده تحویل می‌دهد."""

    enrollment: Enrollment
    created: bool
    access_granted: bool


def synchronize_course_enrollment_stats(course):
    """شمار ثبت‌نام فعال و وضعیت تکمیل ظرفیت دوره را یک‌جا همگام می‌کند."""
    active_count = course.enrollments.exclude(status="cancelled").count()
    is_full = bool(course.capacity) and active_count >= course.capacity
    Course.objects.filter(pk=course.pk).update(
        enroll_count=active_count,
        is_full=is_full,
    )
    course.enroll_count = active_count
    course.is_full = is_full


def enroll_student(*, student, course):
    """دانش‌آموز را با کنترل اتمیک تکرار، مهلت، ظرفیت و پرداخت ثبت‌نام می‌کند."""
    if course.status != "published":
        raise CourseServiceError("این دوره در دسترس نیست.")
    if course.enrollment_deadline and course.enrollment_deadline < timezone.now():
        raise CourseServiceError("مهلت ثبت‌نام این دوره به پایان رسیده است.")

    try:
        with transaction.atomic():
            locked_course = Course.objects.select_for_update().get(pk=course.pk)
            enrollment = Enrollment.objects.filter(
                student=student,
                course=locked_course,
            ).first()

            if enrollment and enrollment.status != "cancelled":
                raise CourseServiceError("شما قبلاً در این دوره ثبت‌نام کرده‌اید.")

            active_count = locked_course.enrollments.exclude(
                status="cancelled"
            ).count()
            if locked_course.capacity and active_count >= locked_course.capacity:
                raise CourseServiceError("ظرفیت این دوره تکمیل شده است.")

            is_free_course = locked_course.is_free
            payment_status = "free" if is_free_course else "pending"
            price_paid = 0
            defaults = {
                "status": "active",
                "payment_status": payment_status,
                "price_paid": price_paid,
                "progress_percentage": 0,
                "completed_at": None,
            }

            if enrollment is None:
                enrollment = Enrollment.objects.create(
                    student=student,
                    course=locked_course,
                    **defaults,
                )
                created = True
            else:
                for field_name, value in defaults.items():
                    setattr(enrollment, field_name, value)
                enrollment.save(update_fields=list(defaults))
                created = False

            synchronize_course_enrollment_stats(locked_course)
    except IntegrityError as exc:
        raise CourseServiceError("ثبت‌نام هم‌زمان تکراری شناسایی شد.") from exc

    # تا زمان افزودن درگاه، دورهٔ پولی pending می‌ماند و محتوای آن باز نمی‌شود.
    access_granted = enrollment.payment_status in ("free", "paid")
    Notification.objects.create(
        user=student,
        title=f"ثبت‌نام در «{course.title}»",
        message=(
            "ثبت‌نام انجام شد و می‌توانی دوره را شروع کنی."
            if access_granted
            else "ثبت‌نام اولیه انجام شد و دسترسی پس از پرداخت فعال می‌شود."
        ),
        link=course.get_absolute_url(),
    )
    return EnrollmentResult(enrollment, created, access_granted)


def mark_lesson_completed(*, user, lesson):
    """پیشرفت یک جلسه را idempotent به حالت تکمیل‌شده می‌برد."""
    progress, _created = LessonProgress.objects.get_or_create(
        lesson=lesson,
        user=user,
    )
    if not progress.is_completed:
        progress.is_completed = True
        progress.completion_percentage = 100
        progress.completed_at = timezone.now()
        progress.save(
            update_fields=(
                "is_completed",
                "completion_percentage",
                "completed_at",
                "last_watched",
            )
        )
    return progress


def add_lesson_comment(*, user, lesson, text):
    """نظر معتبر جلسه را ذخیره و شمارندهٔ نظرات تأییدشده را همگام می‌کند."""
    normalized_text = text.strip()
    if not normalized_text:
        raise CourseServiceError("متن نظر نمی‌تواند خالی باشد.")

    with transaction.atomic():
        comment = LessonComment.objects.create(
            lesson=lesson,
            user=user,
            text=normalized_text,
            is_approved=True,
        )
        approved_count = lesson.comments.filter(is_approved=True).count()
        lesson.comment_count = approved_count
        lesson.save(update_fields=("comment_count",))
    return comment


def synchronize_course_rating_stats(course):
    """میانگین و تعداد امتیازهای دوره را با دادهٔ واقعی دیتابیس همگام می‌کند."""
    rating_summary = course.ratings.aggregate(average_score=Avg("score"))
    rating_count = course.ratings.count()
    course.rating_avg = round(rating_summary["average_score"] or 0, 2)
    course.rating_count = rating_count
    course.save(update_fields=("rating_avg", "rating_count"))


def set_course_rating(*, user, course, score, comment=""):
    """امتیاز کاربر را ثبت و خلاصهٔ امتیاز دوره را در یک تراکنش همگام می‌کند."""
    try:
        normalized_score = int(score)
    except (TypeError, ValueError) as exc:
        raise CourseServiceError("امتیاز نامعتبر است.") from exc
    if not 1 <= normalized_score <= 5:
        raise CourseServiceError("امتیاز باید بین ۱ تا ۵ باشد.")

    with transaction.atomic():
        locked_course = Course.objects.select_for_update().get(pk=course.pk)
        rating, created = CourseRating.objects.update_or_create(
            course=locked_course,
            user=user,
            defaults={"score": normalized_score, "comment": comment.strip()},
        )
        synchronize_course_rating_stats(locked_course)
    return rating, created
