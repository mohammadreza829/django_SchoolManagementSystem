"""
View های اپ کوییز (سبک function-based — هماهنگ با بقیه‌ی پروژه).

جریان کار:
  quiz_list   → لیست آزمون‌هایی که کاربر اجازه‌ی دیدنشون رو داره
  quiz_detail → معرفی آزمون + دکمه شروع (فقط برای ثبت‌نام‌شده‌ها)
  take_quiz   → GET: نمایش سوالات / POST: ثبت پاسخ‌ها و تصحیح خودکار
  quiz_result → نمایش نتیجه + پاسخ صحیح و راه‌حل
  my_progress → نمودار پیشرفت دانش‌آموز در آزمون‌ها

قانون دسترسی آزمون‌ها:
  • آزمون‌هایی که به دوره‌ای وصلند → فقط دانش‌آموزان ثبت‌نام‌شده
  • استادان دوره و ادمین/کارمندان بدون محدودیت
  • آزمون بدون دوره (عمومی) → برای همه قابل دیدن
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

from .models import Quiz, QuizAttempt
from .policies import bypass_quiz_schedule, can_access_quiz, is_quiz_admin
from .services import (
    QuizServiceError,
    finalize_attempt,
    get_or_create_open_attempt,
    sweep_expired_attempts,
)

from Enrollment.models import Enrollment


# ============================================================
# لیست آزمون‌ها
# ============================================================

def quiz_list(request):
    """فهرست آزمون‌های عمومی، ثبت‌نام‌شده یا متعلق به استاد را نمایش می‌دهد."""
    sweep_expired_attempts(request.user)
    base_queryset = Quiz.objects.filter(is_published=True).select_related("course")
    user = request.user

    if is_quiz_admin(user):
        quizzes = base_queryset
    elif user.is_authenticated:
        enrolled_course_ids = Enrollment.objects.filter(
            student=user,
            status="active",
            payment_status__in=("free", "paid"),
        ).values_list("course_id", flat=True)
        quizzes = base_queryset.filter(
            Q(course__isnull=True)
            | Q(course_id__in=enrolled_course_ids)
            | Q(course__teachers=user)
        ).distinct()
    else:
        quizzes = base_queryset.filter(course__isnull=True)

    return render(
        request,
        "quiz/quiz_list.html",
        {"quizzes": quizzes.order_by("-created_at")},
    )


# ============================================================
# جزئیات آزمون
# ============================================================

def quiz_detail(request, slug):
    """صفحه‌ی معرفی آزمون + سوابق تلاش‌های کاربر."""
    sweep_expired_attempts(request.user)
    quiz = get_object_or_404(Quiz, slug=slug, is_published=True)

    # کنترل دسترسی: فقط ثبت‌نام‌شده‌های دوره + استاد دوره + ادمین
    if not can_access_quiz(request.user, quiz):
        if not request.user.is_authenticated:
            messages.warning(request, "برای دیدن این آزمون باید وارد حساب کاربریت بشی.")
            return redirect("accounts:login")
        messages.error(
            request,
            "این آزمون فقط برای دانش‌آموزان ثبت‌نام‌شده در دوره‌ی مربوطه قابل دیدن است.",
        )
        if quiz.course:
            return redirect("courses:course_detail", slug=quiz.course.slug)
        return redirect("quiz:quiz_list")

    user_attempts = []
    attempts_left = None
    if request.user.is_authenticated:
        user_attempts = QuizAttempt.objects.filter(
            quiz=quiz, student=request.user, status=QuizAttempt.COMPLETED
        )
        if quiz.max_attempts > 0:
            # ✅ فیکس: منفی نشدن تعداد تلاش‌های باقی‌مانده
            attempts_left = max(quiz.max_attempts - user_attempts.count(), 0)

    context = {
        "quiz": quiz,
        "user_attempts": user_attempts,
        "attempts_left": attempts_left,
    }
    return render(request, "quiz/quiz_detail.html", context)


# ============================================================
# شرکت در آزمون
# ============================================================

@login_required
def take_quiz(request, slug):
    """نمایش یا ثبت آزمون را با تکیه بر policy و سرویس تراکنشی انجام می‌دهد."""
    quiz = get_object_or_404(Quiz, slug=slug, is_published=True)
    if not can_access_quiz(request.user, quiz):
        messages.error(request, "برای شرکت در این آزمون دسترسی لازم را ندارید.")
        return redirect("quiz:quiz_detail", slug=quiz.slug)

    if not bypass_quiz_schedule(request.user, quiz) and not quiz.is_open_now:
        message = (
            "هنوز زمان شروع این آزمون فرا نرسیده است."
            if quiz.availability_status == "upcoming"
            else "مهلت شرکت در این آزمون به پایان رسیده است."
        )
        messages.error(request, message)
        return redirect("quiz:quiz_detail", slug=quiz.slug)

    questions = quiz.get_questions()
    if not questions:
        messages.error(request, "این آزمون هنوز سوالی ندارد.")
        return redirect("quiz:quiz_detail", slug=quiz.slug)

    try:
        attempt = get_or_create_open_attempt(quiz=quiz, user=request.user)
    except QuizServiceError as exc:
        messages.error(request, str(exc))
        return redirect("quiz:quiz_detail", slug=quiz.slug)

    if attempt.is_expired:
        attempt = finalize_attempt(
            attempt=attempt,
            post_data=request.POST if request.method == "POST" else None,
            questions=questions,
        )
        messages.info(request, "زمان آزمون پایان یافت و پاسخ‌ها ثبت شدند.")
        return redirect("quiz:quiz_result", attempt_id=attempt.id)

    if request.method == "POST":
        attempt = finalize_attempt(
            attempt=attempt,
            post_data=request.POST,
            questions=questions,
        )
        messages.success(request, "آزمون با موفقیت ثبت شد ✅")
        return redirect("quiz:quiz_result", attempt_id=attempt.id)

    remaining_seconds = attempt.remaining_seconds
    return render(
        request,
        "quiz/quiz_take.html",
        {
            "quiz": quiz,
            "questions": questions,
            "attempt": attempt,
            "has_time_limit": remaining_seconds is not None,
            "remaining_seconds": remaining_seconds or 0,
        },
    )


# ============================================================
# نتیجه و پیشرفت
# ============================================================

@login_required
def quiz_result(request, attempt_id):
    """نمایش نتیجه‌ی یک تلاش (فقط صاحب تلاش یا ادمین)."""
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("quiz"), id=attempt_id
    )

    if attempt.student != request.user and not request.user.is_staff:
        messages.error(request, "شما اجازه‌ی دیدن این نتیجه را ندارید.")
        return redirect("quiz:quiz_list")

    answers = attempt.answers.select_related("question").prefetch_related(
        "question__choices", "selected_choices"
    )

    context = {
        "attempt": attempt,
        "quiz": attempt.quiz,
        "answers": answers,
    }
    return render(request, "quiz/quiz_result.html", context)


@login_required
def my_progress(request):
    """نمودار پیشرفت دانش‌آموز در آزمون‌ها."""
    sweep_expired_attempts(request.user)
    completed = (
        QuizAttempt.objects.filter(
            student=request.user, status=QuizAttempt.COMPLETED
        )
        .select_related("quiz")
        .order_by("started_at")
    )

    progress_data = [
        {
            "label": a.quiz.title,
            "value": a.percentage,
            "passed": a.is_passed,
        }
        for a in completed
    ]

    total = completed.count()
    passed = sum(1 for a in completed if a.is_passed)
    avg = round(sum(a.percentage for a in completed) / total, 1) if total else 0

    context = {
        "attempts": completed.order_by("-started_at"),
        "progress_data": progress_data,
        "stats": {"total": total, "passed": passed, "avg": avg},
    }
    return render(request, "quiz/my_progress.html", context)
