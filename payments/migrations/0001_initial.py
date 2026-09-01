import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("courses", "0001_initial"),
        ("Enrollment", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=0, max_digits=10, verbose_name="مبلغ (تومان)")),
                ("authority", models.CharField(blank=True, db_index=True, max_length=64, verbose_name="کد Authority زرین‌پال")),
                ("ref_id", models.CharField(blank=True, max_length=64, verbose_name="کد رهگیری (RefID)")),
                ("status", models.CharField(choices=[("initiated", "شروع‌شده"), ("paid", "پرداخت‌شده"), ("failed", "ناموفق")], default="initiated", max_length=20, verbose_name="وضعیت")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="آخرین به‌روزرسانی")),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payments", to="courses.course", verbose_name="دوره")),
                ("enrollment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payments", to="Enrollment.enrollment", verbose_name="ثبت‌نام")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payments", to=settings.AUTH_USER_MODEL, verbose_name="کاربر")),
            ],
            options={
                "verbose_name": "پرداخت",
                "verbose_name_plural": "پرداخت‌ها",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["status", "created_at"], name="payment_status_created_idx"),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.UniqueConstraint(condition=models.Q(("authority__gt", "")), fields=("authority",), name="payment_authority_unique_when_set"),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.CheckConstraint(condition=models.Q(("amount__gte", 0)), name="payment_amount_nonnegative"),
        ),
    ]
