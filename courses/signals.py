# courses/signals.py

from django.db.models.signals import pre_save, post_save, m2m_changed
from django.dispatch import receiver
from django.utils.text import slugify
from django.utils import timezone
from .models import Course, Lesson, LessonProgress, CourseRating


@receiver(pre_save, sender=Course)
def course_pre_save(sender, instance, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.title)
    if instance.status == "published" and not instance.published_at:
        instance.published_at = timezone.now()


@receiver(pre_save, sender=Lesson)
def lesson_pre_save(sender, instance, **kwargs):
    if not instance.slug:
        base_slug = slugify(instance.title)
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
