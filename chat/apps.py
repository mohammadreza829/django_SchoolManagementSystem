"""پیکربندی و نام نمایشی اپ چت دوره‌ها را تعریف می‌کند.

 
"""

from django.apps import AppConfig


class ChatConfig(AppConfig):
    """پیکربندی، نام فنی و عنوان نمایشی این اپ Django را تعریف می‌کند."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "chat"
    verbose_name = "چت دوره‌ها"
