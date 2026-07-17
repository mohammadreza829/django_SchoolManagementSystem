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
    _sweep_expired_attempts(request.user)

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
    _sweep_expired_attempts(request.user)
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

def _attempts_exhausted(quiz, user):
    """آیا کاربر به حداکثر دفعات مجاز (تلاش‌های تکمیل‌شده) رسیده؟"""
    if quiz.max_attempts <= 0:
        return False
    done = QuizAttempt.objects.filter(
        quiz=quiz, student=user, status=QuizAttempt.COMPLETED
    ).count()
    return done >= quiz.max_attempts


def _finalize_attempt(attempt, post_data, questions):
    """
    ثبت پاسخ‌ها (در صورت ارسال) + تصحیح خودکار + نهایی‌کردن تلاش.
    post_data می‌تواند None باشد (مثلاً وقتی زمان بدون ارسال تمام شده):
    در این حالت هر سوالِ بی‌پاسخ نمره صفر می‌گیرد.
    """
    if attempt.status == QuizAttempt.COMPLETED:
        return

    with transaction.atomic():
        for q in questions:
            ans, _created = AttemptAnswer.objects.get_or_create(
                attempt=attempt, question=q
            )
            field_name = f"question_{q.id}"

            if post_data is not None:
                if q.question_type in (Question.SINGLE, Question.TRUE_FALSE):
                    choice_id = post_data.get(field_name)
                    if choice_id:
                        ans.selected_choices.set(
                            Choice.objects.filter(id=choice_id, question=q)
                        )
                elif q.question_type == Question.MULTIPLE:
                    choice_ids = post_data.getlist(field_name)
                    if choice_ids:
                        ans.selected_choices.set(
                            Choice.objects.filter(id__in=choice_ids, question=q)
                        )
                else:  # numeric یا short
                    ans.answer_text = (post_data.get(field_name) or "").strip()
                    ans.save(update_fields=["answer_text"])

            ans.grade()

        attempt.calculate_score()


def _sweep_expired_attempts(user):
    """
    تلاش‌های «در حال انجامِ» منقضی‌شده‌ی کاربر را خودکار ثبت و نمره‌گذاری می‌کند.
    تضمین می‌کند حتی اگر کاربر صفحه را ببندد، بعد از پایان زمان نمره ثبت شود.
    """
    if not user.is_authenticated:
        return
    in_progress = QuizAttempt.objects.filter(
        student=user, status=QuizAttempt.IN_PROGRESS
    ).select_related("quiz")
    for expired_attempt in in_progress:
        if expired_attempt.is_expired:
            _finalize_attempt(
                expired_attempt,
                None,
                expired_attempt.quiz.get_questions(),
            )


@login_required
def take_quiz(request, slug):
    """قلب اپ: نمایش سوالات، مدیریت زمان سمت سرور و تصحیح خودکار."""
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

    # کنترل بازه‌ی فعال بودن آزمون (ادمین/استاد مستثنا هستند)
    if not _is_privileged(request.user) and not quiz.is_open_now:
        if quiz.availability_status == "upcoming":
            messages.error(request, "هنوز زمان شروع این آزمون فرا نرسیده است.")
        else:
            messages.error(request, "مهلت شرکت در این آزمون به پایان رسیده است.")
        return redirect("quiz:quiz_detail", slug=quiz.slug)

    questions = quiz.get_questions()
    if not questions:
        messages.error(request, "این آزمون هنوز سوالی ندارد.")
        return redirect("quiz:quiz_detail", slug=quiz.slug)

    # تلاشِ در حال انجامِ فعلی کاربر (در صورت وجود) — برای ادامه‌ی همان آزمون
    attempt = (
        QuizAttempt.objects.filter(
            quiz=quiz, student=request.user, status=QuizAttempt.IN_PROGRESS
        )
        .order_by("-started_at")
        .first()
    )

    # اگر زمان همان تلاش تمام شده باشد → خودکار ثبت، نمره‌گذاری و رفتن به نتیجه
    if attempt and attempt.is_expired:
        _finalize_attempt(
            attempt,
            request.POST if request.method == "POST" else None,
            questions,
        )
        messages.info(
            request, "زمان آزمون به پایان رسید و پاسخ‌های شما به‌صورت خودکار ثبت شد."
        )
        return redirect("quiz:quiz_result", attempt_id=attempt.id)

    # ---------- ثبت پاسخ‌ها (POST) ----------
    if request.method == "POST":
        with transaction.atomic():
            if attempt is None:
                if _attempts_exhausted(quiz, request.user):
                    messages.error(
                        request, "شما به حداکثر دفعات مجاز برای این آزمون رسیده‌اید."
                    )
                    return redirect("quiz:quiz_detail", slug=quiz.slug)
                # ✅ فیکس race condition: اگر دو درخواست همزمان برسند،
                # get_or_create مانع ساخته‌شدن دو تلاشِ موازی می‌شود
                attempt, _ = QuizAttempt.objects.get_or_create(
                    quiz=quiz,
                    student=request.user,
                    status=QuizAttempt.IN_PROGRESS,
                    defaults={"max_score": quiz.total_points},
                )
            _finalize_attempt(attempt, request.POST, questions)

        messages.success(request, "آزمون با موفقیت ثبت شد ✅")
        return redirect("quiz:quiz_result", attempt_id=attempt.id)

    # ---------- نمایش فرم آزمون (GET) ----------
    # اگر تلاش در حال انجامی نیست، یک تلاش تازه بساز (با کنترل دفعات مجاز)
    if attempt is None:
        if _attempts_exhausted(quiz, request.user):
            messages.error(request, "شما به حداکثر دفعات مجاز برای این آزمون رسیده‌اید.")
            return redirect("quiz:quiz_detail", slug=quiz.slug)
        # ✅ فیکس race condition: جلوگیری از ساخته‌شدن چند تلاشِ «در حال انجام» موازی
        attempt, _ = QuizAttempt.objects.get_or_create(
            quiz=quiz,
            student=request.user,
            status=QuizAttempt.IN_PROGRESS,
            defaults={"max_score": quiz.total_points},
        )

    remaining = attempt.remaining_seconds  # None یعنی بدون محدودیت زمانی
    context = {
        "quiz": quiz,
        "questions": questions,
        "attempt": attempt,
        "has_time_limit": remaining is not None,
        "remaining_seconds": remaining if remaining is not None else 0,
    }
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
    _sweep_expired_attempts(request.user)
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
