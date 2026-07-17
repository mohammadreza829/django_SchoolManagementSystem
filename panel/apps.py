"""پیکربندی و نام نمایشی اپ پنل مدیریت را تعریف می‌کند.

 
"""

from django.apps import AppConfig


class PanelConfig(AppConfig):
    """پیکربندی، نام فنی و عنوان نمایشی این اپ Django را تعریف می‌کند."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "panel"
    verbose_name = "پنل مدیریت"
