"""سیاست‌های متمرکز دسترسی به دوره و محتوای آموزشی را تعریف می‌کند.

قرارگرفتن قواعد مجوز در این فایل باعث می‌شود view، چت، آزمون و سرویس‌ها از
یک منبع حقیقت مشترک استفاده کنند و رفتار نقش‌ها با هم ناسازگار نشود.
"""

from Enrollment.models import Enrollment


def is_course_teacher(user, course):
    """مشخص می‌کند کاربر استاد همان دوره یا مدیر سامانه است."""
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff or getattr(user, "role", "") == "admin":
        return True
    return course.teachers.filter(pk=user.pk).exists()


def has_course_access(user, course):
    """دسترسی معتبر به محتوای دوره را بر اساس نقش و ثبت‌نام بررسی می‌کند."""
    if not user.is_authenticated:
        return False
    if is_course_teacher(user, course):
        return True
    return Enrollment.objects.filter(
        student=user,
        course=course,
        status="active",
        payment_status__in=("free", "paid"),
    ).exists()


def can_rate_course(user, course):
    """فقط دانش‌آموز دارای ثبت‌نام غیرلغوشده را مجاز به امتیازدهی می‌داند."""
    if not user.is_authenticated:
        return False
    return Enrollment.objects.filter(
        student=user,
        course=course,
        status__in=("active", "completed"),
        payment_status__in=("free", "paid"),
    ).exists()
