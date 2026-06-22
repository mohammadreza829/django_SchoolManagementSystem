from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("courses", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseMessage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("text", models.TextField(verbose_name="متن پیام")),
                (
                    "is_announcement",
                    models.BooleanField(default=False, verbose_name="اعلان استاد"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="زمان ارسال"),
                ),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="courses.course",
                        verbose_name="دوره",
                    ),
                ),
                (
                    "sender",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="course_messages",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="فرستنده",
                    ),
                ),
            ],
            options={
                "verbose_name": "پیام دوره",
                "verbose_name_plural": "پیام‌های دوره",
                "ordering": ["created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="coursemessage",
            index=models.Index(
                fields=["course", "created_at"], name="chat_course_crs_crt_idx"
            ),
        ),
    ]
