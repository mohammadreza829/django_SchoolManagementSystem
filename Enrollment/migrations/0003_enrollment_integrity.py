"""یکپارچگی و indexهای مسیر ثبت‌نام را تقویت می‌کند."""

from django.db import migrations, models


def normalize_enrollment_progress(apps, schema_editor):
    """درصدهای قدیمی را پیش از فعال‌شدن CheckConstraint اصلاح می‌کند."""
    Enrollment = apps.get_model("Enrollment", "Enrollment")
    for enrollment in Enrollment.objects.all().iterator():
        normalized = min(max(enrollment.progress_percentage, 0), 100)
        if normalized != enrollment.progress_percentage:
            enrollment.progress_percentage = normalized
            enrollment.save(update_fields=["progress_percentage"])


class Migration(migrations.Migration):
    """رابطهٔ یکتا، درصد معتبر و index وضعیت دوره را در دیتابیس اعمال می‌کند."""

    dependencies = [("Enrollment", "0002_initial")]

    operations = [
        migrations.RunPython(normalize_enrollment_progress, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name="enrollment",
            unique_together=set(),
        ),
        migrations.AddIndex(
            model_name="enrollment",
            index=models.Index(
                fields=["course", "status", "payment_status"],
                name="enroll_course_state_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="enrollment",
            constraint=models.UniqueConstraint(
                fields=("student", "course"),
                name="enrollment_student_course_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="enrollment",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    progress_percentage__gte=0,
                    progress_percentage__lte=100,
                ),
                name="enroll_progress_0_100",
            ),
        ),
    ]
