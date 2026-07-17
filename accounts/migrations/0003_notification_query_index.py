"""Index ترکیبی اعلان‌های خوانده‌نشده را اضافه می‌کند."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Schema اعلان‌ها را برای query رایج هدر و صفحهٔ اعلان بهینه می‌کند."""

    dependencies = [("accounts", "0002_notification_link")]

    operations = [
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["user", "is_read", "-created_at"],
                name="acct_notif_unread_idx",
            ),
        ),
    ]
