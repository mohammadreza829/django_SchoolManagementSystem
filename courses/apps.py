"""پیکربندی و نام نمایشی اپ دوره‌های آموزشی را تعریف می‌کند.

این فایل بخشی از پروژهٔ مدرسهٔ آنلاین است و مسئولیت‌های آن عمداً در همین دامنه نگه داشته شده‌اند.
"""

# courses/apps.py

from django.apps import AppConfig


class CoursesConfig(AppConfig):
    """پیکربندی، نام فنی و عنوان نمایشی این اپ Django را تعریف می‌کند."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'courses'
    verbose_name = 'دوره‌های آموزشی'