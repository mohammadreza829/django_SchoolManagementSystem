from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Enrollment


def _update_enroll_count(course):
    """تعداد ثبت‌نام‌های فعال هر دوره را به‌روز می‌کند و پرچم ظرفیت را تنظیم می‌کند."""
    active = course.enrollments.exclude(status="cancelled").count()
    course.enroll_count = active
    course.is_full = bool(course.capacity) and active >= course.capacity
    course.save(update_fields=["enroll_count", "is_full"])


@receiver(post_save, sender=Enrollment)
def enrollment_saved(sender, instance, **kwargs):
    _update_enroll_count(instance.course)


@receiver(post_delete, sender=Enrollment)
def enrollment_deleted(sender, instance, **kwargs):
    _update_enroll_count(instance.course)
