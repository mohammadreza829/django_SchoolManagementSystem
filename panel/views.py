"""داشبورد و عملیات مدیریتی دوره، آزمون، سؤال و نتایج را با کنترل دسترسی سطح شیء مدیریت می‌کند.

 
"""

# panel/views.py
import csv
import json
from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Max, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify

from courses.models import Course
from quiz.models import Quiz, Question, QuizQuestion, QuizAttempt

from .forms import CourseForm, QuizForm, QuestionForm, ChoiceFormSet


# ============================ دسترسی و کمکی ============================
def _is_platform_admin(user):
    """مشخص می‌کند کاربر مدیر سامانه یا superuser است یا نه."""
    return bool(user.is_superuser or getattr(user, "role", None) == "admin")


def staff_required(view):
    """فقط استاد یا ادمین به پنل دسترسی دارد."""

    @wraps(view)
    @login_required
    def _wrapped(request, *args, **kwargs):
        """منطق مربوط به عملیات «_wrapped» را اجرا می‌کند."""
        user = request.user
        if _is_platform_admin(user) or getattr(user, "role", None) == "teacher":
            return view(request, *args, **kwargs)
        raise PermissionDenied("شما به پنل مدیریت دسترسی ندارید.")

    return _wrapped


def _get_manageable_courses(user):
    """دوره‌هایی را برمی‌گرداند که کاربر اجازهٔ مدیریتشان را دارد."""
    courses_queryset = Course.objects.all()
    if not _is_platform_admin(user):
        courses_queryset = courses_queryset.filter(teachers=user)
    return courses_queryset.distinct()


def _get_manageable_quizzes(user):
    """آزمون‌هایی را برمی‌گرداند که کاربر اجازهٔ مدیریتشان را دارد."""
    quizzes_queryset = Quiz.objects.all()
    if not _is_platform_admin(user):
        quizzes_queryset = quizzes_queryset.filter(
            Q(created_by=user) | Q(course__teachers=user)
        )
    return quizzes_queryset.distinct()


def get_course_or_403(request, pk):
    """دوره را دریافت می‌کند و در صورت نداشتن مجوز، خطای دسترسی می‌دهد."""
    course = get_object_or_404(Course, pk=pk)
    if not (_is_platform_admin(request.user) or course.teachers.filter(id=request.user.id).exists()):
        raise PermissionDenied("به این دوره دسترسی ندارید.")
    return course


def get_quiz_or_403(request, pk):
    """آزمون را دریافت می‌کند و در صورت نداشتن مجوز، خطای دسترسی می‌دهد."""
    quiz = get_object_or_404(Quiz, pk=pk)
    owner = quiz.created_by_id == request.user.id
    teaches = bool(quiz.course_id) and quiz.course.teachers.filter(id=request.user.id).exists()
    if not (_is_platform_admin(request.user) or owner or teaches):
        raise PermissionDenied("به این آزمون دسترسی ندارید.")
    return quiz


def _unique_slug(model, title, fallback):
    """بر اساس عنوان، یک slug آزاد و یکتا برای مدل مورد نظر می‌سازد."""
    base = slugify(title, allow_unicode=True) or fallback
    slug = base
    i = 2
    while model.objects.filter(slug=slug).exists():
        slug = f"{base}-{i}"
        i += 1
    return slug


# ============================ داشبورد ============================
@staff_required
def dashboard(request):
    """آمار کلیدی و نمودارهای پنل را برای دوره‌ها و آزمون‌های مجاز آماده می‌کند."""
    courses = _get_manageable_courses(request.user)
    quizzes = _get_manageable_quizzes(request.user)
    attempts = QuizAttempt.objects.filter(quiz__in=quizzes, status="completed")

    kpis = {
        "courses": courses.count(),
        "quizzes": quizzes.count(),
        "attempts": attempts.count(),
        "students": attempts.values("student").distinct().count(),
    }

    # روند شرکت در ۱۴ روز اخیر
    today = timezone.localdate()
    start = today - timedelta(days=13)
    attempts_per_day = {}
    recent_attempts = attempts.filter(completed_at__date__gte=start)
    for attempt in recent_attempts:
        if attempt.completed_at:
            completion_date = timezone.localtime(attempt.completed_at).date()
            attempts_per_day[completion_date] = attempts_per_day.get(completion_date, 0) + 1

    # محور افقی نمودار همیشه شامل چهارده روز کامل، حتی روزهای بدون آزمون، است.
    daily_labels, daily_values = [], []
    for day_offset in range(14):
        current_date = start + timedelta(days=day_offset)
        daily_labels.append(current_date.strftime("%m/%d"))
        daily_values.append(attempts_per_day.get(current_date, 0))

    # آزمون‌های پرتکرار برای جلوگیری از شلوغی نمودار به هشت مورد محدود می‌شوند.
    quiz_statistics = (
        attempts.values("quiz__title")
        .annotate(
            average_percentage=Avg("percentage"),
            attempt_count=Count("id"),
        )
        .order_by("-attempt_count")[:8]
    )
    quiz_labels = [row["quiz__title"] for row in quiz_statistics]
    quiz_avg = [
        round(row["average_percentage"] or 0, 1)
        for row in quiz_statistics
    ]

    passed = attempts.filter(is_passed=True).count()
    failed = attempts.count() - passed

    recent = attempts.select_related("student", "quiz").order_by("-completed_at")[:8]

    context = {
        "kpis": kpis,
        "daily_labels": json.dumps(daily_labels, ensure_ascii=False),
        "daily_values": json.dumps(daily_values),
        "quiz_labels": json.dumps(quiz_labels, ensure_ascii=False),
        "quiz_avg": json.dumps(quiz_avg),
        "pass_fail": json.dumps([passed, failed]),
        "recent": recent,
    }
    return render(request, "panel/dashboard.html", context)


# ============================ دوره‌ها ============================
@staff_required
def course_list(request):
    """فهرست دوره‌های مجاز را با فیلتر و مرتب‌سازی مناسب نمایش می‌دهد."""
    q = request.GET.get("q", "").strip()
    courses = _get_manageable_courses(request.user).order_by("-created_at")
    if q:
        courses = courses.filter(title__icontains=q)
    return render(request, "panel/course_list.html", {"courses": courses, "q": q})


@staff_required
def course_create(request):
    """فرم ساخت دوره را پردازش و مالکیت استاد را ثبت می‌کند."""
    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            if not course.slug:
                course.slug = _unique_slug(Course, course.title, "course")
            course.save()
            form.save_m2m()
            if not _is_platform_admin(request.user):
                course.teachers.add(request.user)
            messages.success(request, "دوره با موفقیت ساخته شد.")
            return redirect("panel:course_list")
    else:
        form = CourseForm()
    return render(request, "panel/course_form.html", {"form": form, "mode": "new"})


@staff_required
def course_edit(request, pk):
    """دورهٔ مجاز را دریافت و تغییرات فرم را ذخیره می‌کند."""
    course = get_course_or_403(request, pk)
    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "تغییرات ذخیره شد.")
            return redirect("panel:course_list")
    else:
        form = CourseForm(instance=course)
    return render(request, "panel/course_form.html", {"form": form, "mode": "edit", "obj": course})


@staff_required
def course_delete(request, pk):
    """پس از بررسی مجوز و روش درخواست، دوره را حذف می‌کند."""
    course = get_course_or_403(request, pk)
    if request.method == "POST":
        course.delete()
        messages.success(request, "دوره حذف شد.")
    return redirect("panel:course_list")


@staff_required
def course_toggle_publish(request, pk):
    """وضعیت انتشار دوره را بین پیش‌نویس و منتشرشده تغییر می‌دهد."""
    course = get_course_or_403(request, pk)
    if request.method == "POST":
        course.status = "draft" if course.status == "published" else "published"
        course.save(update_fields=["status"])
        messages.success(request, "وضعیت دوره تغییر کرد.")
    return redirect("panel:course_list")


# ============================ آزمون‌ها ============================
@staff_required
def quiz_list(request):
    """فهرست آزمون‌های قابل مشاهده یا مدیریت کاربر را نمایش می‌دهد."""
    quizzes = _get_manageable_quizzes(request.user).select_related("course").order_by("-created_at")
    return render(request, "panel/quiz_list.html", {"quizzes": quizzes})


@staff_required
def quiz_create(request):
    """فرم ساخت آزمون را پردازش و سازندهٔ آن را ثبت می‌کند."""
    if request.method == "POST":
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.created_by = request.user
            quiz.slug = _unique_slug(Quiz, quiz.title, "quiz")
            quiz.save()
            messages.success(request, "آزمون ساخته شد. حالا سوالات را اضافه کنید.")
            return redirect("panel:quiz_questions", pk=quiz.pk)
    else:
        form = QuizForm()
    return render(request, "panel/quiz_form.html", {"form": form, "mode": "new"})


@staff_required
def quiz_edit(request, pk):
    """آزمون مجاز را دریافت و تغییرات فرم را ذخیره می‌کند."""
    quiz = get_quiz_or_403(request, pk)
    if request.method == "POST":
        form = QuizForm(request.POST, instance=quiz)
        if form.is_valid():
            form.save()
            messages.success(request, "تغییرات آزمون ذخیره شد.")
            return redirect("panel:quiz_list")
    else:
        form = QuizForm(instance=quiz)
    return render(request, "panel/quiz_form.html", {"form": form, "mode": "edit", "obj": quiz})


@staff_required
def quiz_delete(request, pk):
    """پس از بررسی مجوز و روش درخواست، آزمون را حذف می‌کند."""
    quiz = get_quiz_or_403(request, pk)
    if request.method == "POST":
        quiz.delete()
        messages.success(request, "آزمون حذف شد.")
    return redirect("panel:quiz_list")


@staff_required
def quiz_toggle_publish(request, pk):
    """وضعیت انتشار آزمون را تغییر می‌دهد."""
    quiz = get_quiz_or_403(request, pk)
    if request.method == "POST":
        quiz.is_published = not quiz.is_published
        quiz.save(update_fields=["is_published"])
        messages.success(request, "وضعیت آزمون تغییر کرد.")
    return redirect("panel:quiz_list")


@staff_required
def quiz_questions(request, pk):
    """سؤال‌های متصل به آزمون را به ترتیب برای مدیریت نمایش می‌دهد."""
    quiz = get_quiz_or_403(request, pk)
    quiz_questions_queryset = quiz.quiz_questions.select_related(
        "question"
    ).order_by("order", "id")
    return render(
        request,
        "panel/quiz_questions.html",
        {"quiz": quiz, "quiz_questions": quiz_questions_queryset},
    )


@staff_required
def question_add(request, pk):
    """سؤال و گزینه‌های آن را ساخته و به آزمون متصل می‌کند."""
    quiz = get_quiz_or_403(request, pk)
    if request.method == "POST":
        form = QuestionForm(request.POST, request.FILES)
        formset = ChoiceFormSet(request.POST, prefix="choices")
        if form.is_valid() and formset.is_valid():
            question = form.save(commit=False)
            question.created_by = request.user
            question.save()
            formset.instance = question
            formset.save()
            next_order = (quiz.quiz_questions.aggregate(m=Max("order"))["m"] or 0) + 1
            QuizQuestion.objects.create(quiz=quiz, question=question, order=next_order)
            messages.success(request, "سوال اضافه شد.")
            return redirect("panel:quiz_questions", pk=quiz.pk)
    else:
        form = QuestionForm()
        formset = ChoiceFormSet(prefix="choices")
    return render(
        request,
        "panel/question_form.html",
        {"quiz": quiz, "form": form, "formset": formset},
    )


@staff_required
def question_remove(request, pk, qq_id):
    """ارتباط سؤال انتخاب‌شده با آزمون را حذف می‌کند."""
    quiz = get_quiz_or_403(request, pk)
    if request.method == "POST":
        QuizQuestion.objects.filter(id=qq_id, quiz=quiz).delete()
        messages.success(request, "سوال از آزمون حذف شد.")
    return redirect("panel:quiz_questions", pk=quiz.pk)


# ============================ نتایج و نمرات ============================
@staff_required
def results(request):
    """خلاصهٔ آمار نتایج آزمون‌های مجاز را نمایش می‌دهد."""
    quizzes = (
        _get_manageable_quizzes(request.user)
        .annotate(
            attempt_count=Count("attempts", filter=Q(attempts__status="completed")),
            avg_score=Avg("attempts__percentage", filter=Q(attempts__status="completed")),
        )
        .order_by("-attempt_count")
    )
    return render(request, "panel/results.html", {"quizzes": quizzes})


def _quiz_attempts(quiz):
    """تلاش‌های تکمیل‌شدهٔ آزمون را همراه با اطلاعات دانش‌آموز برمی‌گرداند."""
    return quiz.attempts.filter(status="completed").select_related("student")


@staff_required
def quiz_results(request, pk):
    """نتایج و آمار قبولی یک آزمون را نمایش می‌دهد."""
    quiz = get_quiz_or_403(request, pk)
    attempts = _quiz_attempts(quiz).order_by("-percentage")
    total = attempts.count()
    passed = attempts.filter(is_passed=True).count()
    percentage_summary = attempts.aggregate(
        average_percentage=Avg("percentage")
    )
    stats = {
        "count": total,
        "passed": passed,
        "failed": total - passed,
        "avg": percentage_summary["average_percentage"] or 0,
    }
    return render(
        request,
        "panel/quiz_results.html",
        {"quiz": quiz, "attempts": attempts, "stats": stats},
    )


@staff_required
def quiz_results_csv(request, pk):
    """نتایج آزمون را در قالب فایل CSV فارسی تولید می‌کند."""
    quiz = get_quiz_or_403(request, pk)
    attempts = _quiz_attempts(quiz).order_by("-percentage")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="results_quiz_{quiz.pk}.csv"'
    response.write("\ufeff")  # BOM تا اکسل فارسی را درست بخواند
    writer = csv.writer(response)
    writer.writerow(["دانش‌آموز", "نام کاربری", "نمره", "از", "درصد", "نتیجه", "تاریخ"])
    for a in attempts:
        completed = (
            timezone.localtime(a.completed_at).strftime("%Y-%m-%d %H:%M")
            if a.completed_at
            else ""
        )
        writer.writerow([
            a.student.get_full_name() or a.student.username,
            a.student.username,
            a.score,
            a.max_score,
            a.percentage,
            "قبول" if a.is_passed else "مردود",
            completed,
        ])
    return response


@staff_required
def attempt_detail(request, attempt_id):
    """جزئیات پاسخ‌ها و نمرهٔ یک تلاش آزمون را نمایش می‌دهد."""
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("student", "quiz"), pk=attempt_id
    )
    get_quiz_or_403(request, attempt.quiz_id)  # کنترل دسترسی
    answers = attempt.answers.select_related("question").prefetch_related("selected_choices")
    return render(
        request,
        "panel/attempt_detail.html",
        {"attempt": attempt, "answers": answers},
    )
