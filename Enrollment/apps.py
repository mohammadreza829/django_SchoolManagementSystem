"""پیکربندی اپ Enrollment و بارگذاری signalهای مربوط به شمارندهٔ ثبت‌نام را انجام می‌دهد.

 
"""

from django.apps import AppConfig


class EnrollmentConfig(AppConfig):
    """پیکربندی، نام فنی و عنوان نمایشی این اپ Django را تعریف می‌کند."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "Enrollment"
    verbose_name = "ثبت‌نام‌ها"

    def ready(self):
        # اتصال signalها هنگام بالا آمدن اپ
        """هنگام آماده‌شدن اپ، signalهای مورد نیاز را ثبت می‌کند."""
        from . import signals  # noqa: F401
