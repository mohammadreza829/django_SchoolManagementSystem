"""پیکربندی و نام نمایشی اپ آزمون‌ها را تعریف می‌کند.

 
"""

from django.apps import AppConfig


class QuizConfig(AppConfig):
    """پیکربندی، نام فنی و عنوان نمایشی این اپ Django را تعریف می‌کند."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "quiz"
    verbose_name = "آزمون‌ها"
