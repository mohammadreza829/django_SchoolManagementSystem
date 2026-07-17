"""Constraintها و indexهای صحت آزمون و تلاش را اضافه می‌کند."""

from django.db import migrations, models
from django.db.models import Count


def normalize_quiz_data(apps, schema_editor):
    """مقادیر نامعتبر و تلاش‌های باز تکراری را پیش از constraint اصلاح می‌کند."""
    Question = apps.get_model("quiz", "Question")
    Quiz = apps.get_model("quiz", "Quiz")
    QuizAttempt = apps.get_model("quiz", "QuizAttempt")

    Question.objects.filter(numeric_tolerance__lt=0).update(numeric_tolerance=0)
    for quiz in Quiz.objects.all().iterator():
        normalized = min(max(quiz.pass_mark, 0), 100)
        if normalized != quiz.pass_mark:
            quiz.pass_mark = normalized
            quiz.save(update_fields=["pass_mark"])

    duplicate_groups = (
        QuizAttempt.objects.filter(status="in_progress")
        .values("quiz_id", "student_id")
        .annotate(open_count=Count("id"))
        .filter(open_count__gt=1)
    )
    for group in duplicate_groups.iterator():
        attempts = QuizAttempt.objects.filter(
            quiz_id=group["quiz_id"],
            student_id=group["student_id"],
            status="in_progress",
        ).order_by("-started_at", "-id")
        keep_attempt = attempts.first()
        attempts.exclude(pk=keep_attempt.pk).update(
            status="completed",
            completed_at=models.F("started_at"),
        )


class Migration(migrations.Migration):
    """حد نصاب، tolerance و یکتایی تلاش باز را در دیتابیس تضمین می‌کند."""

    dependencies = [("quiz", "0005_alter_quizattempt_status")]

    operations = [
        migrations.RunPython(normalize_quiz_data, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="quizattempt",
            index=models.Index(
                fields=["student", "quiz", "status", "started_at"],
                name="quiz_attempt_state_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="question",
            constraint=models.CheckConstraint(
                condition=models.Q(numeric_tolerance__gte=0),
                name="question_tolerance_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="quiz",
            constraint=models.CheckConstraint(
                condition=models.Q(pass_mark__gte=0, pass_mark__lte=100),
                name="quiz_pass_mark_0_100",
            ),
        ),
        migrations.AddConstraint(
            model_name="quizattempt",
            constraint=models.UniqueConstraint(
                fields=("quiz", "student"),
                condition=models.Q(status="in_progress"),
                name="one_open_attempt_per_student",
            ),
        ),
    ]
