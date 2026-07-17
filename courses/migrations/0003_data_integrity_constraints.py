"""Constraintها و indexهای یکپارچگی دادهٔ دوره را اضافه می‌کند."""

from django.db import migrations, models
from django.utils.text import slugify


def normalize_course_data(apps, schema_editor):
    """داده‌های قدیمی را پیش از فعال‌شدن constraintهای جدید پاک‌سازی می‌کند."""
    Course = apps.get_model("courses", "Course")
    Lesson = apps.get_model("courses", "Lesson")
    LessonProgress = apps.get_model("courses", "LessonProgress")
    CourseRating = apps.get_model("courses", "CourseRating")

    for course in Course.objects.all().iterator():
        changed = []
        normalized_discount = min(max(course.discount_percent, 0), 100)
        if normalized_discount != course.discount_percent:
            course.discount_percent = normalized_discount
            changed.append("discount_percent")
        if course.price < 0:
            course.price = 0
            changed.append("price")
        if changed:
            course.save(update_fields=changed)

    used_slugs_by_course = {}
    lessons = Lesson.objects.order_by("course_id", "order", "id")
    for lesson in lessons.iterator():
        used_slugs = used_slugs_by_course.setdefault(lesson.course_id, set())
        base_slug = slugify(lesson.title, allow_unicode=True) or f"lesson-{lesson.order or 1}"
        candidate = lesson.slug or base_slug
        suffix = 2
        while candidate in used_slugs:
            candidate = f"{base_slug}-{suffix}"
            suffix += 1
        used_slugs.add(candidate)
        if lesson.slug != candidate:
            lesson.slug = candidate
            lesson.save(update_fields=["slug"])

    for progress in LessonProgress.objects.all().iterator():
        normalized = min(max(progress.completion_percentage, 0), 100)
        if normalized != progress.completion_percentage:
            progress.completion_percentage = normalized
            progress.save(update_fields=["completion_percentage"])

    for rating in CourseRating.objects.all().iterator():
        normalized = min(max(rating.score, 1), 5)
        if normalized != rating.score:
            rating.score = normalized
            rating.save(update_fields=["score"])


class Migration(migrations.Migration):
    """قواعد درصد، قیمت، slug، پیشرفت و امتیاز را در سطح دیتابیس enforce می‌کند."""

    dependencies = [("courses", "0002_course_capacity")]

    operations = [
        migrations.RunPython(normalize_course_data, migrations.RunPython.noop),
        migrations.RemoveIndex(
            model_name="course",
            name="courses_cou_slug_2e551f_idx",
        ),
        migrations.AlterUniqueTogether(
            name="courserating",
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name="lesson",
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name="lessonprogress",
            unique_together=set(),
        ),
        migrations.AddIndex(
            model_name="lessonprogress",
            index=models.Index(
                fields=["user", "is_completed", "lesson"],
                name="lesson_prog_user_done_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="course",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    discount_percent__gte=0,
                    discount_percent__lte=100,
                ),
                name="course_discount_0_100",
            ),
        ),
        migrations.AddConstraint(
            model_name="course",
            constraint=models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name="course_price_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="lesson",
            constraint=models.UniqueConstraint(
                fields=("course", "order"),
                name="lesson_course_order_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="lesson",
            constraint=models.UniqueConstraint(
                fields=("course", "slug"),
                name="lesson_course_slug_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="lessonprogress",
            constraint=models.UniqueConstraint(
                fields=("lesson", "user"),
                name="lesson_progress_user_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="lessonprogress",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    completion_percentage__gte=0,
                    completion_percentage__lte=100,
                ),
                name="lesson_progress_pct_0_100",
            ),
        ),
        migrations.AddConstraint(
            model_name="courserating",
            constraint=models.UniqueConstraint(
                fields=("course", "user"),
                name="course_rating_user_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="courserating",
            constraint=models.CheckConstraint(
                condition=models.Q(score__gte=1, score__lte=5),
                name="course_rating_score_1_5",
            ),
        ),
    ]
