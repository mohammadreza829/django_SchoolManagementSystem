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
from django.db import transaction
from django.db.models import Q

from .models import Quiz, QuizAttempt, AttemptAnswer, Choice, Question

try:
    from Enrollment.models import Enrollment
    ENROLLMENT_AVAILABLE = True
except ImportError:
    ENROLLMENT_AVAILABLE = False


# ============================================================
# توابع کمکی برای کنترل دسترسی
# ============================================================

def _is_privileged(user):
    """ادمین، کارمند یا استاد؟"""
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.is_staff or getattr(user, "is_teacher", False)


def _is_enrolled(user, course):
    """آیا کاربر در این دوره ثبت‌نام فعال داره؟"""
    if not user.is_authenticated or course is None:
        return False
    if not ENROLLMENT_AVAILABLE:
        return False
    return Enrollment.objects.filter(
        student=user,
        course=course,
        status="active",
        payment_status__in=["free", "paid"],
    ).exists()


def _can_access_quiz(user, quiz):
    """آیا کاربر اجازه‌ی دیدن / شرکت در این آزمون رو داره؟"""
    if _is_privileged(user):
        return True
    # آزمون عمومی (بدون دوره) — در دسترس همه
    if quiz.course is None:
        return True
    # استاد خود دوره
    if user.is_authenticated and quiz.course.teachers.filter(id=user.id).exists():
        return True
    return _is_enrolled(user, quiz.course)


# ============================================================
# لیست آزمون‌ها
# ============================================================

def quiz_list(request):
    """لیست آزمون‌هایی که کاربر اجازه‌ی دیدنشون رو داره."""
    base_qs = (
        Quiz.objects.filter(is_published=True)
        .select_related("course")
        .order_by("-created_at")
    )

    user = request.user

    if _is_privileged(user):
        # ادمین‌ها/استادان، همه رو می‌بینن
        quizzes = base_qs
    elif user.is_authenticated and ENROLLMENT_AVAILABLE:
        # دوره‌هایی که کاربر ثبت‌نام فعال داره
        enrolled_course_ids = Enrollment.objects.filter(
            student=user,
            status="active",
            payment_status__in=["free", "paid"],
        ).values_list("course_id", flat=True)

        quizzes = base_qs.filter(
            Q(course__isnull=True) | Q(course_id__in=enrolled_course_ids)
        )
    else:
        # کاربر مهمان، فقط آزمون‌های عمومی (بدون دوره) رو می‌بینه
        quizzes = base_qs.filter(course__isnull=True)

    return render(request, "quiz/quiz_list.html", {"quizzes": quizzes})


# ============================================================
# جزئیات آزمون
# ============================================================

def quiz_detail(request, slug):
    """صفحه‌ی معرفی آزمون + سوابق تلاش‌های کاربر."""
    quiz = get_object_or_404(Quiz, slug=slug, is_published=True)

    # کنترل دسترسی: فقط ثبت‌نام‌شده‌های دوره + استاد دوره + ادمین
    if not _can_access_quiz(request.user, quiz):
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
            attempts_left = quiz.max_attempts - user_attempts.count()

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
    """قلب اپ: نمایش سوالات و تصحیح خودکار."""
    quiz = get_object_or_404(Quiz, slug=slug, is_published=True)

    # کنترل دسترسی: فقط ثبت‌نام‌شده‌های دوره مجاز به شرکت در آزمون هستند
    if not _can_access_quiz(request.user, quiz):
        messages.error(
            request,
            "برای شرکت در این آزمون باید در دوره‌ی مربوطه ثبت‌نام کرده باشید.",
        )
        if quiz.course:
            return redirect("courses:course_detail", slug=quiz.course.slug)
        return redirect("quiz:quiz_list")

    questions = quiz.get_questions()

    # آزمون بدون سوال نباید قابل شروع باشد
    if not questions:
        messages.error(request, "این آزمون هنوز سوالی ندارد.")
        return redirect("quiz:quiz_detail", slug=quiz.slug)

    # کنترل تعداد دفعات مجاز
    if quiz.max_attempts > 0:
        done = QuizAttempt.objects.filter(
            quiz=quiz, student=request.user, status=QuizAttempt.COMPLETED
        ).count()
        if done >= quiz.max_attempts:
            messages.error(request, "شما به حداکثر دفعات مجاز برای این آزمون رسیده‌اید.")
            return redirect("quiz:quiz_detail", slug=quiz.slug)

    # ---------- ثبت پاسخ‌ها ----------
    if request.method == "POST":
        with transaction.atomic():
            locked_quiz = Quiz.objects.select_for_update().get(id=quiz.id)
            if locked_quiz.max_attempts > 0:
                done = QuizAttempt.objects.filter(
                    quiz=quiz, student=request.user, status=QuizAttempt.COMPLETED
                ).count()
                if done >= locked_quiz.max_attempts:
                    messages.error(
                        request, "شما به حداکثر دفعات مجاز برای این آزمون رسیده‌اید."
                    )
                    return redirect("quiz:quiz_detail", slug=quiz.slug)

            attempt = QuizAttempt.objects.create(
                quiz=quiz, student=request.user, max_score=quiz.total_points
            )

            for q in questions:
                ans = AttemptAnswer.objects.create(attempt=attempt, question=q)
                field_name = f"question_{q.id}"

                if q.question_type in (Question.SINGLE, Question.TRUE_FALSE):
                    choice_id = request.POST.get(field_name)
                    if choice_id:
                        ans.selected_choices.set(
                            Choice.objects.filter(id=choice_id, question=q)
                        )

                elif q.question_type == Question.MULTIPLE:
                    choice_ids = request.POST.getlist(field_name)
                    if choice_ids:
                        ans.selected_choices.set(
                            Choice.objects.filter(id__in=choice_ids, question=q)
                        )

                else:  # numeric یا short
                    ans.answer_text = request.POST.get(field_name, "").strip()
                    ans.save(update_fields=["answer_text"])

                ans.grade()

            attempt.calculate_score()

        messages.success(request, "آزمون با موفقیت ثبت شد ✅")
        return redirect("quiz:quiz_result", attempt_id=attempt.id)

    # ---------- نمایش فرم آزمون ----------
    context = {"quiz": quiz, "questions": questions}
    return render(request, "quiz/quiz_take.html", context)


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
