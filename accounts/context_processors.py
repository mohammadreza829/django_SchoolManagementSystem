"""
Context processor‌های اپ accounts.

شمارنده‌ی اعلان‌های خوانده‌نشده را به صورت سراسری در اختیار همه‌ی قالب‌ها
قرار می‌دهد تا روی زنگوله‌ی بالای صفحه نمایش داده شود.
"""

# نگاشت ارقام لاتین به فارسی برای نمایش زیباتر روی نشان (badge)
_PERSIAN_DIGITS = str.maketrans("0123456789", "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9")


def _to_persian(value):
    return str(value).translate(_PERSIAN_DIGITS)


def notifications_processor(request):
    """
    تعداد اعلان‌های خوانده‌نشده‌ی کاربر فعلی را برمی‌گرداند.

    - unread_notifications_count: عدد خام (برای شرط نمایش/مخفی کردن نشان)
    - unread_notifications_display: رشته‌ی فارسیِ آماده‌ی نمایش (مثلاً ۳ یا ۹۹+)
    """
    count = 0
    user = getattr(request, "user", None)

    if user is not None and user.is_authenticated:
        count = user.notifications.filter(is_read=False).count()

    if count > 99:
        display = "\u06f9\u06f9+"  # ۹۹+
    else:
        display = _to_persian(count)

    return {
        "unread_notifications_count": count,
        "unread_notifications_display": display,
    }
