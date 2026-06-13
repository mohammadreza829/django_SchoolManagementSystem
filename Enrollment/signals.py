from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Enrollment


def _update_enroll_count(course):
    """تعداد ثبت‌نام‌های هر دوره را به‌روز می‌کند."""
    course.enroll_count = course.enrollments.count()
    course.save(update_fields=["enroll_count"])


@receiver(post_save, sender=Enrollment)
def enrollment_saved(sender, instance, **kwargs):
    _update_enroll_count(instance.course)


@receiver(post_delete, sender=Enrollment)
def enrollment_deleted(sender, instance, **kwargs):
    _update_enroll_count(instance.course)
