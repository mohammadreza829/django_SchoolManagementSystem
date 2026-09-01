"""کلاینت درگاه پرداخت زرین‌پال (نسخهٔ REST v4).

این ماژول فقط ارتباط HTTP با زرین‌پال را می‌داند و از منطق دامنه بی‌خبر است؛
سرویس‌های payments.services از آن استفاده می‌کنند. آدرس‌ها بر اساس فلگ
ZARINPAL_SANDBOX بین محیط تستی (sandbox) و واقعی سوییچ می‌کنند.
"""

import requests
from django.conf import settings


class ZarinpalError(Exception):
    """خطای قابل‌نمایش هنگام گفت‌وگو با درگاه زرین‌پال."""


_ERROR_MESSAGES = {
    -9: "اطلاعات ارسالی به درگاه نامعتبر است.",
    -10: "شناسهٔ پذیرنده یا IP نامعتبر است.",
    -11: "درخواست یافت نشد.",
    -50: "مبلغ پرداخت با مبلغ تأیید هم‌خوان نیست.",
    -51: "پرداخت ناموفق بود.",
    -53: "پرداخت متعلق به این پذیرنده نیست.",
    -54: "کد Authority نامعتبر است.",
}


def _api_base():
    if settings.ZARINPAL_SANDBOX:
        return "https://sandbox.zarinpal.com/pg/v4/payment"
    return "https://payment.zarinpal.com/pg/v4/payment"


def _startpay_base():
    if settings.ZARINPAL_SANDBOX:
        return "https://sandbox.zarinpal.com/pg/StartPay/"
    return "https://payment.zarinpal.com/pg/StartPay/"


def _gateway_amount(amount_toman):
    """قیمت دوره‌ها تومان است؛ زرین‌پال پیش‌فرض ریال می‌گیرد مگر currency=IRT."""
    if settings.ZARINPAL_CURRENCY == "IRT":
        return int(amount_toman)
    return int(amount_toman) * 10


def _extract_error(payload):
    errors = payload.get("errors")
    code = None
    if isinstance(errors, dict):
        code = errors.get("code")
    elif isinstance(errors, list) and errors:
        first = errors[0]
        if isinstance(first, dict):
            code = first.get("code")
    if code is None:
        return "پاسخ نامعتبر از درگاه پرداخت دریافت شد."
    return _ERROR_MESSAGES.get(code, f"خطای درگاه پرداخت (کد {code}).")


def request_payment(*, amount_toman, callback_url, description, email="", mobile=""):
    """یک تراکنش در زرین‌پال باز می‌کند و (authority, gateway_url) برمی‌گرداند."""
    if not settings.ZARINPAL_MERCHANT_ID:
        raise ZarinpalError("شناسهٔ پذیرندهٔ زرین‌پال تنظیم نشده است.")

    metadata = {}
    if email:
        metadata["email"] = email
    if mobile:
        metadata["mobile"] = mobile

    payload = {
        "merchant_id": settings.ZARINPAL_MERCHANT_ID,
        "amount": _gateway_amount(amount_toman),
        "currency": settings.ZARINPAL_CURRENCY,
        "callback_url": callback_url,
        "description": description,
    }
    if metadata:
        payload["metadata"] = metadata

    try:
        response = requests.post(
            f"{_api_base()}/request.json",
            json=payload,
            timeout=settings.ZARINPAL_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise ZarinpalError("ارتباط با درگاه پرداخت برقرار نشد.") from exc
    except ValueError as exc:
        raise ZarinpalError("پاسخ نامعتبر از درگاه پرداخت دریافت شد.") from exc

    result = data.get("data")
    if not result or result.get("code") not in (100, 101):
        raise ZarinpalError(_extract_error(data))

    authority = result.get("authority")
    if not authority:
        raise ZarinpalError("کد Authority از درگاه دریافت نشد.")

    return authority, f"{_startpay_base()}{authority}"


def verify_payment(*, amount_toman, authority):
    """تراکنش را تأیید می‌کند و (ref_id, already_verified) برمی‌گرداند."""
    if not settings.ZARINPAL_MERCHANT_ID:
        raise ZarinpalError("شناسهٔ پذیرندهٔ زرین‌پال تنظیم نشده است.")

    payload = {
        "merchant_id": settings.ZARINPAL_MERCHANT_ID,
        "amount": _gateway_amount(amount_toman),
        "authority": authority,
    }

    try:
        response = requests.post(
            f"{_api_base()}/verify.json",
            json=payload,
            timeout=settings.ZARINPAL_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise ZarinpalError("ارتباط با درگاه پرداخت برقرار نشد.") from exc
    except ValueError as exc:
        raise ZarinpalError("پاسخ نامعتبر از درگاه پرداخت دریافت شد.") from exc

    result = data.get("data")
    if not result or result.get("code") not in (100, 101):
        raise ZarinpalError(_extract_error(data))

    already_verified = result.get("code") == 101  # 101 = قبلاً تأیید شده
    ref_id = str(result.get("ref_id") or "")
    return ref_id, already_verified
