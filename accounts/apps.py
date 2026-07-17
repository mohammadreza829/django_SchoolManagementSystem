"""پیکربندی اپ accounts و فعال‌سازی signalهای ساخت پروفایل را انجام می‌دهد.

 
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """پیکربندی، نام فنی و عنوان نمایشی این اپ Django را تعریف می‌کند."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        """هنگام آماده‌شدن اپ، signalهای مورد نیاز را ثبت می‌کند."""
        import accounts.signals
