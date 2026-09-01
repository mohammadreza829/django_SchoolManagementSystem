"""ویوهای شروع و بازگشت پرداخت زرین‌پال.

این لایه فقط ورودی HTTP و پیام کاربر را مدیریت می‌کند؛ کل منطق در
payments.services و payments.gateways است.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from courses.models import Course

from .services import PaymentServiceError, start_payment, verify_payment


@login_required
def start(request, course_slug):
    """آغاز پرداخت: ساخت تراکنش و هدایت کاربر به درگاه زرین‌پال."""
    course = get_object_or_404(Course, slug=course_slug, status="published")

    if request.method != "POST":
        return redirect("courses:checkout", course_slug=course_slug)

    callback_url = request.build_absolute_uri(reverse("payments:callback"))
    try:
        gateway_url = start_payment(
            user=request.user,
            course=course,
            callback_url=callback_url,
        )
    except PaymentServiceError as exc:
        messages.error(request, str(exc))
        return redirect("courses:checkout", course_slug=course_slug)

    return redirect(gateway_url)


def callback(request):
    """بازگشت از درگاه؛ تأیید تراکنش و باز کردن دسترسی دوره.

    عمداً login_required ندارد: کاربر ممکن است هنگام بازگشت از بانک سشنش
    منقضی شده باشد؛ تراکنش با Authority پیدا و به کاربر همان تراکنش نسبت
    داده می‌شود، نه به request.user.
    """
    authority = request.GET.get("Authority", "")
    gateway_status = request.GET.get("Status", "")

    try:
        payment, ok = verify_payment(
            authority=authority,
            gateway_status=gateway_status,
        )
    except PaymentServiceError as exc:
        messages.error(request, str(exc))
        return redirect("courses:course_list")

    course = payment.course
    if ok:
        messages.success(
            request,
            (
                f"پرداخت با موفقیت انجام شد ✅ کد رهگیری: {payment.ref_id}"
                if payment.ref_id
                else "پرداخت با موفقیت انجام شد و دوره کامل باز شد ✅"
            ),
        )
    else:
        messages.error(
            request,
            "پرداخت ناموفق بود یا لغو شد. می‌تونی دوباره تلاش کنی.",
        )
    return redirect("courses:course_detail", slug=course.slug)
