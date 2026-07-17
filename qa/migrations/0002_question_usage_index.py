"""Index سهمیه و تاریخچهٔ پرسش‌های هوش مصنوعی را اضافه می‌کند."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Queryهای کاربر، وضعیت و تاریخ پرسش را برای quota بهینه می‌کند."""

    dependencies = [("qa", "0001_initial")]

    operations = [
        migrations.AddIndex(
            model_name="aiquestion",
            index=models.Index(
                fields=["user", "status", "created_at"],
                name="qa_user_status_date_idx",
            ),
        ),
    ]
