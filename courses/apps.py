# courses/apps.py

from django.apps import AppConfig


class CoursesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'courses'
    verbose_name = 'دوره‌های آموزشی'

    def ready(self):
        import courses.signals  # ثبت سیگنال‌ها