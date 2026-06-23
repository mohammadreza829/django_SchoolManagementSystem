"""
View های چت‌روم دوره (HTTP + polling).

  course_chat   → صفحه‌ی چت‌روم
  messages_json → اندپوینت JSON برای گرفتن پیام‌های جدید (polling)
  post_message  → ثبت پیام جدید (فقط POST)
دسترسی: استاد دوره یا دانش‌آموز ثبت‌نام‌شده‌ی همان دوره (یا ادمین).
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.utils import timezone

from courses.models import Course
from Enrollment.models import Enrollment
from accounts.models import Notification
from .models import CourseMessage


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


def _serialize(msg, user):
    local = timezone.localtime(msg.created_at)
    return {
        "id": msg.id,
        "text": msg.text,
        "is_announcement": msg.is_announcement,
        "sender": msg.sender.get_full_name() or msg.sender.username,
        "is_teacher": _is_teacher_of(msg.sender, msg.course),
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
    course = get_object_or_404(Course, id=course_id)
    if not _can_access_chat(request.user, course):
        return HttpResponseForbidden("no access")

    qs = course.messages.select_related("sender", "course").order_by("created_at")
    after = request.GET.get("after")
    if after and after.isdigit():
        qs = qs.filter(id__gt=int(after))
    qs = qs[:200]

    data = [_serialize(m, request.user) for m in qs]
    return JsonResponse({"messages": data})


@login_required
@require_POST
def post_message(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if not _can_access_chat(request.user, course):
        return HttpResponseForbidden("no access")

    text = (request.POST.get("text") or "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "empty"}, status=400)

    is_teacher = _is_teacher_of(request.user, course)
    is_announcement = is_teacher and request.POST.get("is_announcement") == "1"

    msg = CourseMessage.objects.create(
        course=course,
        sender=request.user,
        text=text[:2000],
        is_announcement=is_announcement,
    )

    # اگر فرستنده استاد یا ادمین بود، برای دانش‌آموزان ثبت‌نام‌شده‌ی فعال نوتیفیکیشن بساز
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
        from django.urls import reverse
        chat_url = reverse("chat:room", args=[course.id])
        notif_title = ("اعلان استاد" if is_announcement else "پیام جدید") + f" «{course.title}»"
        notifications = [
            Notification(user_id=sid, message=notif_text, link=chat_url, title=notif_title)
            for sid in student_ids
        ]
        if notifications:
            Notification.objects.bulk_create(notifications)

    return JsonResponse({"ok": True, "message": _serialize(msg, request.user)})
