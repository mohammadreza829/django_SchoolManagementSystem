"""پیکربندی و نام نمایشی اپ پرسش‌وپاسخ هوشمند را تعریف می‌کند.

 
"""

from django.apps import AppConfig


class QaConfig(AppConfig):
    """پیکربندی، نام فنی و عنوان نمایشی این اپ Django را تعریف می‌کند."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "qa"
    verbose_name = "پرسش و پاسخ هوشمند"
