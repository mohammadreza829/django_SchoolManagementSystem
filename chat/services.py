"""عملیات تغییردهندهٔ چت و ساخت اعلان‌های وابسته را پیاده‌سازی می‌کند."""

from django.core.cache import cache
from django.db import transaction
from django.urls import reverse

from accounts.models import Notification
from courses.policies import is_course_teacher
from Enrollment.models import Enrollment

from .models import CourseMessage

MAX_MESSAGE_LENGTH = 2000
RATE_LIMIT_SECONDS = 2


class ChatServiceError(Exception):
    """خطای قابل نمایش در عملیات ارسال پیام چت است."""


def create_course_message(*, user, course, text, announce=False):
    """پیام را اعتبارسنجی و ذخیره و اعلان مخاطبان را به‌صورت گروهی ایجاد می‌کند."""
    normalized_text = text.strip()
    if not normalized_text:
        raise ChatServiceError("پیام خالی است.")
    if len(normalized_text) > MAX_MESSAGE_LENGTH:
        raise ChatServiceError(
            f"پیام حداکثر می‌تواند {MAX_MESSAGE_LENGTH} کاراکتر باشد."
        )

    rate_key = f"chat_rate_{user.id}"
    if not cache.add(rate_key, 1, RATE_LIMIT_SECONDS):
        raise ChatServiceError("کمی آهسته‌تر! چند لحظه صبر کن.")

    sender_is_teacher = is_course_teacher(user, course)
    is_announcement = sender_is_teacher and announce

    with transaction.atomic():
        message = CourseMessage.objects.create(
            course=course,
            sender=user,
            text=normalized_text,
            is_announcement=is_announcement,
        )
        if sender_is_teacher:
            _create_student_notifications(message)
    return message


def _create_student_notifications(message):
    """اعلان پیام استاد را برای دانش‌آموزان فعال دوره به‌صورت batch ایجاد می‌کند."""
    student_ids = Enrollment.objects.filter(
        course=message.course,
        status="active",
        payment_status__in=("free", "paid"),
    ).exclude(student=message.sender).values_list("student_id", flat=True)

    preview = (
        message.text[:80] + "…"
        if len(message.text) > 80
        else message.text
    )
    label = "اعلان استاد" if message.is_announcement else "پیام جدید از استاد"
    chat_url = reverse("chat:room", args=(message.course_id,))
    notifications = (
        Notification(
            user_id=student_id,
            title=f"{label} «{message.course.title}»",
            message=f"{label} در دورهٔ «{message.course.title}»: {preview}",
            link=chat_url,
        )
        for student_id in student_ids.iterator(chunk_size=1000)
    )
    Notification.objects.bulk_create(notifications, batch_size=1000)
