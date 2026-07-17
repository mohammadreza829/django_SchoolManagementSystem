"""پیش از ذخیره، slug و زمان انتشار را تنظیم می‌کند و آمار امتیاز دوره را همگام نگه می‌دارد.

این فایل بخشی از پروژهٔ مدرسهٔ آنلاین است و مسئولیت‌های آن عمداً در همین دامنه نگه داشته شده‌اند.
"""

# courses/signals.py

from django.db.models.signals import pre_save, post_save, m2m_changed
from django.dispatch import receiver
from django.utils.text import slugify
from django.utils import timezone
from .models import Course, Lesson, LessonProgress, CourseRating


@receiver(pre_save, sender=Course)
def prepare_course_before_save(sender, instance, **kwargs):
    """پیش از ذخیرهٔ دوره، slug یکتا و زمان اولین انتشار را آماده می‌کند."""
    if not instance.slug:
        base_slug = slugify(instance.title) or "course"
        slug = base_slug
        counter = 1
        while (
            Course.objects.filter(slug=slug).exclude(id=instance.id).exists()
        ):
            slug = f"{base_slug}-{counter}"
            counter += 1
        instance.slug = slug
    if instance.status == "published" and not instance.published_at:
        instance.published_at = timezone.now()


@receiver(pre_save, sender=Lesson)
def prepare_lesson_before_save(sender, instance, **kwargs):
    """پیش از ذخیرهٔ جلسه، slug یکتا در محدودهٔ همان دوره را آماده می‌کند."""
    if not instance.slug:
        base_slug = slugify(instance.title) or f"lesson-{instance.order or 1}"
        slug = base_slug
        counter = 1
        while (
            Lesson.objects.filter(course=instance.course, slug=slug)
            .exclude(id=instance.id)
            .exists()
        ):
            slug = f"{base_slug}-{counter}"
            counter += 1
        instance.slug = slug


# نکته: شمارش enroll_count دیگر در اپ Enrollment (با signal روی مدل Enrollment) انجام می‌شود


@receiver(post_save, sender=CourseRating)
def update_course_rating_on_save(sender, instance, created, **kwargs):
    """
    بعد از ذخیره هر امتیاز، میانگین امتیازات دوره را به‌روز کن
    """
    course = instance.course
    ratings = CourseRating.objects.filter(course=course)

    # به‌روزرسانی تعداد و میانگین امتیازات در مدل Course
    course.rating_count = ratings.count()

    if course.rating_count > 0:
        # محاسبه میانگین
        total_score = sum(r.score for r in ratings)
        course.rating_avg = total_score / course.rating_count
    else:
        course.rating_avg = 0

    # فقط فیلدهای rating_count و rating_avg را ذخیره کن
    course.save(update_fields=["rating_count", "rating_avg"])
