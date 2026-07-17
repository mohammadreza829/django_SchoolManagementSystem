"""
بخش «پرسش‌ها» — پرسش از دستیار هوش مصنوعی.

محدودیت‌ها (قابل تنظیم در settings):
  - سهمیه‌ی روزانه‌ی هر کاربر (AI_DAILY_LIMIT، پیش‌فرض ۱۰).
    سوال‌هایی که با خطا مواجه شوند سهمیه مصرف نمی‌کنند.
  - حداقل/حداکثر طول سوال.
  - فاصله‌ی زمانی بین دو سوال (ضد اسپم و دابل‌کلیک).
  - فقط سوال‌های آموزشی پاسخ داده می‌شوند (کنترل در system prompt +
    ثبت وضعیت rejected برای سوال‌های خارج از محدوده).
"""

import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.utils import timezone

from courses.models import Course

from .models import AiQuestion
from .services import AiServiceError, ask_ai

MIN_LENGTH = 5
MAX_LENGTH = 1000
RATE_LIMIT_SECONDS = 15
HISTORY_SIZE = 20


def _get_daily_question_limit():
    """سقف روزانهٔ پرسش‌های هر کاربر را از تنظیمات پروژه می‌خواند."""
    return getattr(settings, "AI_DAILY_LIMIT", 10)


def _count_questions_used_today(user):
    """تعداد پرسش‌های مصرف‌کنندهٔ سهمیهٔ امروز کاربر را محاسبه می‌کند."""
    today = timezone.localdate()
    return (
        AiQuestion.objects.filter(user=user, created_at__date=today)
        .exclude(status="failed")
        .count()
    )


def _get_accessible_courses(user):
    """دوره‌های مجاز کاربر را برای انتخاب اختیاری در فرم سؤال برمی‌گرداند."""
    if user.is_superuser or getattr(user, "role", "") == "admin":
        return Course.objects.filter(status="published")
    if getattr(user, "is_teacher", False):
        return Course.objects.filter(teachers=user)
    return Course.objects.filter(
        enrollments__student=user,
        enrollments__status="active",
    ).distinct()


@login_required
def ask_page(request):
    """ورودی سؤال را اعتبارسنجی، سهمیه را کنترل، سرویس AI را فراخوانی و تاریخچه را نمایش می‌دهد."""
    limit = _get_daily_question_limit()

    if request.method == "POST":
        question = (request.POST.get("question") or "").strip()
        course = None
        course_id = (request.POST.get("course") or "").strip()
        if course_id.isdigit():
            course = _get_accessible_courses(request.user).filter(id=int(course_id)).first()

        # --- اعتبارسنجی ---
        if len(question) < MIN_LENGTH:
            messages.error(request, "سوال خیلی کوتاه است؛ کمی کامل‌ترش کن.")
            return redirect("qa:ask")
        if len(question) > MAX_LENGTH:
            messages.error(request, f"سوال حداکثر می‌تواند {MAX_LENGTH} کاراکتر باشد.")
            return redirect("qa:ask")

        # --- سهمیه‌ی روزانه ---
        if _count_questions_used_today(request.user) >= limit:
            messages.error(
                request,
                f"سهمیه‌ی امروزت ({limit} سوال) تمام شده. فردا دوباره سر بزن 🙂",
            )
            return redirect("qa:ask")

        # --- ضد اسپم / دابل‌کلیک (cache.add اتمیک است) ---
        rate_key = f"qa_rate_{request.user.id}"
        if not cache.add(rate_key, 1, RATE_LIMIT_SECONDS):
            messages.warning(request, "کمی صبر کن؛ سوال قبلی هنوز در حال پردازش است.")
            return redirect("qa:ask")

        model_used = getattr(settings, "AI_MODEL", "")
        started = time.monotonic()
        try:
            answer, rejected = ask_ai(
                question, course_title=course.title if course else None
            )
        except AiServiceError as exc:
            AiQuestion.objects.create(
                user=request.user,
                course=course,
                question=question,
                answer="",
                status="failed",
                model_used=model_used,
                response_ms=int((time.monotonic() - started) * 1000),
            )
            cache.delete(rate_key)
            messages.error(request, f"دریافت پاسخ ممکن نشد: {exc}")
            return redirect("qa:ask")

        elapsed_ms = int((time.monotonic() - started) * 1000)
        if rejected:
            AiQuestion.objects.create(
                user=request.user,
                course=course,
                question=question,
                answer="",
                status="rejected",
                model_used=model_used,
                response_ms=elapsed_ms,
            )
            messages.warning(
                request,
                "این سوال خارج از محدوده‌ی آموزشی دستیار است؛ لطفاً سوال درسی بپرس 📚",
            )
        else:
            AiQuestion.objects.create(
                user=request.user,
                course=course,
                question=question,
                answer=answer,
                status="answered",
                model_used=model_used,
                response_ms=elapsed_ms,
            )
        return redirect("qa:ask")

    used = _count_questions_used_today(request.user)
    history = (
        AiQuestion.objects.filter(user=request.user)
        .select_related("course")[:HISTORY_SIZE]
    )
    context = {
        "history": history,
        "used": used,
        "limit": limit,
        "remaining": max(limit - used, 0),
        "courses": _get_accessible_courses(request.user),
        "max_length": MAX_LENGTH,
    }
    return render(request, "qa/ask.html", context)
