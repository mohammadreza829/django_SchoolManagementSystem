"""تنظیمات درگاه پرداخت زرین‌پال.

مقادیر از متغیرهای محیطی/فایل .env خوانده می‌شوند (ai_settings آن‌ها را از قبل
در os.environ بار کرده است). هیچ رمزی نباید داخل کد نوشته شود.
"""

import os

# شناسهٔ پذیرنده. برای sandbox می‌توان GUID تستی زیر را نگه داشت.
ZARINPAL_MERCHANT_ID = os.environ.get(
    "ZARINPAL_MERCHANT_ID", "00000000-0000-0000-0000-000000000000"
)

# حالت تستی (sandbox). برای پروداکشن روی False بگذار.
ZARINPAL_SANDBOX = os.environ.get("ZARINPAL_SANDBOX", "True").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

# واحد مبلغ ارسالی به درگاه: IRR (ریال، پیش‌فرض) یا IRT (تومان).
ZARINPAL_CURRENCY = os.environ.get("ZARINPAL_CURRENCY", "IRR").strip() or "IRR"

# مهلت اتصال به درگاه (ثانیه).
try:
    ZARINPAL_TIMEOUT_SECONDS = int(os.environ.get("ZARINPAL_TIMEOUT_SECONDS", "30"))
except ValueError:
    ZARINPAL_TIMEOUT_SECONDS = 30
