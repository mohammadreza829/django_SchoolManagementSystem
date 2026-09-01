"""سرویس‌های تراکنشی پرداخت.

- start_payment: ساخت رکورد Payment و گرفتن آدرس درگاه از زرین‌پال.
- verify_payment: راستی‌آزمایی با زرین‌پال و باز کردن دسترسی از طریق
  courses.services.confirm_enrollment_payment (تنها منبع حقیقتِ باز کردن دسترسی).

منطق atomic و idempotent است تا callback تکراری خطا نسازد.
"""

from django.db import transaction

from courses.services import (
    CourseServiceError,
    PAID_PAYMENT_STATUSES,
    confirm_enrollment_payment,
)
from Enrollment.models import Enrollment

from . import gateways
from .models import Payment


class PaymentServiceError(Exception):
    """خطای قابل‌نمایش مربوط به فرایند پرداخت."""


def _active_enrollment(*, user, course):
    return (
        Enrollment.objects.filter(student=user, course=course)
        .exclude(status="cancelled")
        .first()
    )


def start_payment(*, user, course, callback_url):
    """یک تراکنش پرداخت جدید می‌سازد و آدرس درگاه زرین‌پال را برمی‌گرداند."""
    enrollment = _active_enrollment(user=user, course=course)
    if enrollment is None:
        raise PaymentServiceError("برای پرداخت، اول باید در دوره ثبت‌نام کنی.")
    if enrollment.payment_status in PAID_PAYMENT_STATUSES:
        raise PaymentServiceError("دسترسی این دوره از قبل فعال است.")

    amount = int(course.final_price)
    if amount <= 0:
        raise PaymentServiceError("این دوره رایگان است و نیازی به پرداخت ندارد.")

    payment = Payment.objects.create(
        user=user,
        course=course,
        enrollment=enrollment,
        amount=amount,
        status=Payment.STATUS_INITIATED,
    )

    email = getattr(user, "email", "") or ""
    mobile = getattr(user, "phone", "") or ""

    try:
        authority, gateway_url = gateways.request_payment(
            amount_toman=amount,
            callback_url=callback_url,
            description=f"خرید دورهٔ «{course.title}»",
            email=email,
            mobile=mobile,
        )
    except gateways.ZarinpalError as exc:
        payment.status = Payment.STATUS_FAILED
        payment.save(update_fields=("status", "updated_at"))
        raise PaymentServiceError(str(exc)) from exc

    payment.authority = authority
    payment.save(update_fields=("authority", "updated_at"))
    return gateway_url


def verify_payment(*, authority, gateway_status):
    """پرداخت را تأیید/رد می‌کند؛ خروجی (payment, ok)."""
    if not authority:
        raise PaymentServiceError("کد پیگیری پرداخت نامعتبر است.")

    with transaction.atomic():
        payment = (
            Payment.objects.select_for_update()
            .select_related("course", "user")
            .filter(authority=authority)
            .first()
        )
        if payment is None:
            raise PaymentServiceError("تراکنش پرداخت پیدا نشد.")

        if payment.status == Payment.STATUS_PAID:  # idempotent
            return payment, True

        if gateway_status != "OK":  # کاربر لغو کرد یا درگاه ناموفق
            payment.status = Payment.STATUS_FAILED
            payment.save(update_fields=("status", "updated_at"))
            _mark_enrollment_failed(payment.enrollment_id)
            return payment, False

        try:
            ref_id, _already = gateways.verify_payment(
                amount_toman=int(payment.amount),
                authority=authority,
            )
        except gateways.ZarinpalError as exc:
            payment.status = Payment.STATUS_FAILED
            payment.save(update_fields=("status", "updated_at"))
            _mark_enrollment_failed(payment.enrollment_id)
            raise PaymentServiceError(str(exc)) from exc

        payment.ref_id = ref_id
        payment.status = Payment.STATUS_PAID
        payment.save(update_fields=("ref_id", "status", "updated_at"))

    # باز کردن دسترسی خارج از قفل بالا؛ خودش تراکنش و idempotency دارد.
    try:
        confirm_enrollment_payment(student=payment.user, course=payment.course)
    except CourseServiceError as exc:
        raise PaymentServiceError(str(exc)) from exc

    return payment, True


def _mark_enrollment_failed(enrollment_id):
    """اگر ثبت‌نام در‌انتظار بود، وضعیت پرداختش را ناموفق می‌کند."""
    Enrollment.objects.filter(
        pk=enrollment_id, payment_status="pending"
    ).update(payment_status="failed")
