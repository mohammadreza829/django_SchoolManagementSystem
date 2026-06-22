"""
View های اپ کوییز (سبک function-based — هماهنگ با بقیه‌ی پروژه).

جریان کار:
  quiz_list   → لیست آزمون‌های منتشرشده
  quiz_detail → معرفی آزمون + دکمه شروع
  take_quiz   → GET: نمایش سوالات / POST: ثبت پاسخ‌ها و تصحیح خودکار
  quiz_result → نمایش نتیجه + پاسخ صحیح و راه‌حل
  my_progress → نمودار پیشرفت دانش‌آموز در آزمون‌ها
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from .models import Quiz, QuizAttempt, AttemptAnswer, Choice, Question


def quiz_list(request):
    """لیست همه‌ی آزمون‌های منتشرشده."""
    quizzes = (
        Quiz.objects.filter(is_published=True)
        .select_related("course")
        .order_by("-created_at")
    )
    return render(request, "quiz/quiz_list.html", {"quizzes": quizzes})


def quiz_detail(request, slug):
    """صفحه‌ی معرفی آزمون + سوابق تلاش‌های کاربر."""
    quiz = get_object_or_404(Quiz, slug=slug, is_published=True)

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


@login_required
def take_quiz(request, slug):
    """
    قلب اپ: نمایش سوالات و تصحیح خودکار.
    """
    quiz = get_object_or_404(Quiz, slug=slug, is_published=True)

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
        # کل عملیات اتمیک + قفل ردیف آزمون تا دو ارسال همزمان از سقف دفعات رد نشوند
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

                # تصحیح خودکار همین پاسخ
                ans.grade()

            # جمع نمره کل و تعیین قبولی
            attempt.calculate_score()

        messages.success(request, "آزمون با موفقیت ثبت شد ✅")
        return redirect("quiz:quiz_result", attempt_id=attempt.id)

    # ---------- نمایش فرم آزمون ----------
    context = {"quiz": quiz, "questions": questions}
    return render(request, "quiz/quiz_take.html", context)


@login_required
def quiz_result(request, attempt_id):
    """نمایش نتیجه‌ی یک تلاش (فقط صاحب تلاش یا ادمین)."""
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("quiz"), id=attempt_id
    )

    # کنترل دسترسی: فقط خود دانش‌آموز یا ادمین
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
    """
    نمودار پیشرفت دانش‌آموز در آزمون‌ها.
    دیتای نمودار به صورت لیست پایتون پاس داده می‌شه و در تمپلیت با
    تگ json_script (روش امن جنگو) به JSON تبدیل می‌شه تا Chart.js بخوندش.
    """
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
