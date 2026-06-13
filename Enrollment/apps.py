from django.apps import AppConfig


class EnrollmentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "Enrollment"
    verbose_name = "ثبت‌نام‌ها"

    def ready(self):
        # اتصال signalها هنگام بالا آمدن اپ
        from . import signals  # noqa: F401
