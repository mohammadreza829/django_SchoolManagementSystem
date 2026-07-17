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
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from courses.models import Course

from .models import CourseMessage
from .policies import can_access_course_chat, can_delete_course_message
from .services import ChatServiceError, create_course_message
from courses.policies import is_course_teacher

PAGE_SIZE = 50            # تعداد پیام در هر بار بارگذاری تاریخچه


def _get_course_teacher_ids(course):
    """آی‌دی استادهای دوره — فقط یک کوئری (رفع N+1 نسخه‌ی قبل)."""
    return set(course.teachers.values_list("id", flat=True))


def _is_sender_course_teacher(sender, teacher_ids):
    """چک استاد بودن فرستنده بدون کوئری اضافه."""
    return (
        sender.id in teacher_ids
        or sender.is_superuser
        or sender.is_staff
        or getattr(sender, "role", "") == "admin"
    )


def _serialize_chat_message(message, user, teacher_ids):
    """پیام دیتابیس را به ساختار JSON مورد نیاز رابط چت تبدیل می‌کند."""
    local_created_at = timezone.localtime(message.created_at)
    return {
        "id": message.id,
        "text": message.text,
        "is_announcement": message.is_announcement,
        "sender": message.sender.get_full_name() or message.sender.username,
        "is_teacher": _is_sender_course_teacher(message.sender, teacher_ids),
        "is_mine": message.sender_id == user.id,
        "time": local_created_at.strftime("%H:%M"),
        "date": local_created_at.strftime("%Y/%m/%d"),
    }


@login_required
def course_chat(request, course_id):
    """پس از بررسی دسترسی، صفحهٔ اتاق چت یک دوره را نمایش می‌دهد."""
    course = get_object_or_404(Course, id=course_id)
    if not can_access_course_chat(request.user, course):
        return redirect("courses:course_detail", slug=course.slug)
    context = {
        "course": course,
        "is_teacher": is_course_teacher(request.user, course),
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
    if not can_access_course_chat(request.user, course):
        return HttpResponseForbidden("no access")

    teacher_ids = _get_course_teacher_ids(course)
    messages_queryset = course.messages.select_related("sender")

    after = request.GET.get("after")
    before = request.GET.get("before")
    has_more = False

    if after and after.isdigit():
        messages = list(messages_queryset.filter(id__gt=int(after)).order_by("id")[:200])
    elif before and before.isdigit():
        message_batch = list(
            messages_queryset.filter(id__lt=int(before)).order_by("-id")[: PAGE_SIZE + 1]
        )
        has_more = len(message_batch) > PAGE_SIZE
        messages = list(reversed(message_batch[:PAGE_SIZE]))
    else:
        message_batch = list(messages_queryset.order_by("-id")[: PAGE_SIZE + 1])
        has_more = len(message_batch) > PAGE_SIZE
        messages = list(reversed(message_batch[:PAGE_SIZE]))

    serialized_messages = [
        _serialize_chat_message(message, request.user, teacher_ids)
        for message in messages
    ]
    return JsonResponse({"messages": serialized_messages, "has_more": has_more})


@login_required
@require_POST
def post_message(request, course_id):
    """پس از کنترل دسترسی، ساخت پیام را به سرویس چت واگذار می‌کند."""
    course = get_object_or_404(Course, id=course_id)
    if not can_access_course_chat(request.user, course):
        return HttpResponseForbidden("no access")

    try:
        message = create_course_message(
            user=request.user,
            course=course,
            text=request.POST.get("text", ""),
            announce=request.POST.get("is_announcement") == "1",
        )
    except ChatServiceError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    teacher_ids = _get_course_teacher_ids(course)
    return JsonResponse(
        {
            "ok": True,
            "message": _serialize_chat_message(
                message,
                request.user,
                teacher_ids,
            ),
        }
    )


@login_required
@require_POST
def delete_message(request, course_id, message_id):
    """حذف پیام: فقط فرستنده‌ی پیام یا استاد/ادمین دوره."""
    course = get_object_or_404(Course, id=course_id)
    msg = get_object_or_404(CourseMessage, id=message_id, course=course)
    if not can_delete_course_message(request.user, msg):
        return HttpResponseForbidden("no access")
    msg.delete()
    return JsonResponse({"ok": True})
