"""
View های چت‌روم دوره (HTTP + polling).

  course_chat    → صفحه‌ی چت‌روم
  messages_json  → اندپوینت JSON برای گرفتن پیام‌ها (polling + تاریخچه)
  post_message   → ثبت پیام جدید (فقط POST، با rate-limit)
  delete_message → حذف پیام (فرستنده یا استاد دوره)

دسترسی: استاد دوره یا دانش‌آموز ثبت‌نام‌شده‌ی همان دوره (یا ادمین).

بهبودهای این نسخه نسبت به نسخه‌ی قبلی:
  1) رفع N+1: چک «استاد بودن» فرستنده برای هر پیام یک کوئری جدا می‌زد
     (تا ۲۰۰ کوئری در هر poll!) → حالا آی‌دی استادها یک بار گرفته می‌شود.
  2) رفع باگ بارگذاری اولیه: قبلاً «قدیمی‌ترین» ۲۰۰ پیام برمی‌گشت؛ یعنی در
     چت شلوغ پیام‌های جدید هیچ‌وقت دیده نمی‌شدند! → حالا آخرین ۵۰ پیام
     برمی‌گردد و تاریخچه با پارامتر before صفحه‌بندی می‌شود.
  3) rate-limit ارسال پیام (ضد اسپم).
  4) امکان حذف پیام توسط فرستنده یا استاد دوره.
"""

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Notification
from courses.models import Course
from Enrollment.models import Enrollment

from .models import CourseMessage

PAGE_SIZE = 50            # تعداد پیام در هر بار بارگذاری تاریخچه
MAX_MESSAGE_LENGTH = 2000
RATE_LIMIT_SECONDS = 2    # حداقل فاصله‌ی بین دو پیام هر کاربر


def _is_teacher_of(user, course):
    """آیا کاربر استاد/ادمین این دوره است؟"""
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff or getattr(user, "role", "") == "admin":
        return True
    return course.teachers.filter(id=user.id).exists()


def _can_access_chat(user, course):
    """استاد دوره، ادمین، یا دانش‌آموز ثبت‌نام‌شده‌ی فعال."""
    if not user.is_authenticated:
        return False
    if _is_teacher_of(user, course):
        return True
    return Enrollment.objects.filter(
        student=user,
        course=course,
        status="active",
        payment_status__in=["free", "paid"],
    ).exists()


def _teacher_ids(course):
    """آی‌دی استادهای دوره — فقط یک کوئری (رفع N+1 نسخه‌ی قبل)."""
    return set(course.teachers.values_list("id", flat=True))


def _sender_is_teacher(sender, teacher_ids):
    """چک استاد بودن فرستنده بدون کوئری اضافه."""
    return (
        sender.id in teacher_ids
        or sender.is_superuser
        or sender.is_staff
        or getattr(sender, "role", "") == "admin"
    )


def _serialize(msg, user, teacher_ids):
    local = timezone.localtime(msg.created_at)
    return {
        "id": msg.id,
        "text": msg.text,
        "is_announcement": msg.is_announcement,
        "sender": msg.sender.get_full_name() or msg.sender.username,
        "is_teacher": _sender_is_teacher(msg.sender, teacher_ids),
        "is_mine": msg.sender_id == user.id,
        "time": local.strftime("%H:%M"),
        "date": local.strftime("%Y/%m/%d"),
    }


@login_required
def course_chat(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not _can_access_chat(request.user, course):
        return redirect("courses:course_detail", slug=course.slug)
    context = {
        "course": course,
        "is_teacher": _is_teacher_of(request.user, course),
    }
    return render(request, "chat/room.html", context)


@login_required
def messages_json(request, course_id):
    """
    سه حالت:
      بدون پارامتر      → آخرین PAGE_SIZE پیام (بارگذاری اولیه)
      ?after=<id>       → پیام‌های جدیدتر از id (polling)
      ?before=<id>      → پیام‌های قدیمی‌تر از id (تاریخچه / اسکرول به بالا)
    """
    course = get_object_or_404(Course, id=course_id)
    if not _can_access_chat(request.user, course):
        return HttpResponseForbidden("no access")

    teacher_ids = _teacher_ids(course)
    base = course.messages.select_related("sender")

    after = request.GET.get("after")
    before = request.GET.get("before")
    has_more = False

    if after and after.isdigit():
        msgs = list(base.filter(id__gt=int(after)).order_by("id")[:200])
    elif before and before.isdigit():
        chunk = list(base.filter(id__lt=int(before)).order_by("-id")[: PAGE_SIZE + 1])
        has_more = len(chunk) > PAGE_SIZE
        msgs = list(reversed(chunk[:PAGE_SIZE]))
    else:
        chunk = list(base.order_by("-id")[: PAGE_SIZE + 1])
        has_more = len(chunk) > PAGE_SIZE
        msgs = list(reversed(chunk[:PAGE_SIZE]))

    data = [_serialize(m, request.user, teacher_ids) for m in msgs]
    return JsonResponse({"messages": data, "has_more": has_more})


@login_required
@require_POST
def post_message(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not _can_access_chat(request.user, course):
        return HttpResponseForbidden("no access")

    text = (request.POST.get("text") or "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "پیام خالی است."}, status=400)
    if len(text) > MAX_MESSAGE_LENGTH:
        return JsonResponse(
            {"ok": False, "error": f"پیام حداکثر می‌تواند {MAX_MESSAGE_LENGTH} کاراکتر باشد."},
            status=400,
        )

    # rate-limit: جلوگیری از اسپم (cache.add اتمیک است)
    rate_key = f"chat_rate_{request.user.id}"
    if not cache.add(rate_key, 1, RATE_LIMIT_SECONDS):
        return JsonResponse(
            {"ok": False, "error": "کمی آهسته‌تر! چند لحظه صبر کن."}, status=429
        )

    is_teacher = _is_teacher_of(request.user, course)
    is_announcement = is_teacher and request.POST.get("is_announcement") == "1"

    msg = CourseMessage.objects.create(
        course=course,
        sender=request.user,
        text=text,
        is_announcement=is_announcement,
    )

    # اگر فرستنده استاد یا ادمین بود، برای دانش‌آموزان فعال نوتیفیکیشن بساز
    if is_teacher:
        student_ids = list(
            Enrollment.objects.filter(
                course=course,
                status="active",
                payment_status__in=["free", "paid"],
            ).exclude(student=request.user).values_list("student_id", flat=True)
        )
        preview = (text[:80] + "…") if len(text) > 80 else text
        prefix = "اعلان استاد" if is_announcement else "پیام جدید از استاد"
        notif_text = f"{prefix} در دوره‌ی «{course.title}»: {preview}"
        chat_url = reverse("chat:room", args=[course.id])
        notif_title = ("اعلان استاد" if is_announcement else "پیام جدید") + f" «{course.title}»"
        notifications = [
            Notification(user_id=sid, message=notif_text, link=chat_url, title=notif_title)
            for sid in student_ids
        ]
        if notifications:
            Notification.objects.bulk_create(notifications)

    teacher_ids = _teacher_ids(course)
    return JsonResponse({"ok": True, "message": _serialize(msg, request.user, teacher_ids)})


@login_required
@require_POST
def delete_message(request, course_id, message_id):
    """حذف پیام: فقط فرستنده‌ی پیام یا استاد/ادمین دوره."""
    course = get_object_or_404(Course, id=course_id)
    msg = get_object_or_404(CourseMessage, id=message_id, course=course)
    if not (msg.sender_id == request.user.id or _is_teacher_of(request.user, course)):
        return HttpResponseForbidden("no access")
    msg.delete()
    return JsonResponse({"ok": True})
