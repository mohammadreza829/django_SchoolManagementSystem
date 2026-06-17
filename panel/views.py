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
def is_admin(user):
    return bool(user.is_superuser or getattr(user, "role", None) == "admin")


def staff_required(view):
    """فقط استاد یا ادمین به پنل دسترسی دارد."""

    @wraps(view)
    @login_required
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if is_admin(user) or getattr(user, "role", None) == "teacher":
            return view(request, *args, **kwargs)
        raise PermissionDenied("شما به پنل مدیریت دسترسی ندارید.")

    return _wrapped


def my_courses(user):
    qs = Course.objects.all()
    if not is_admin(user):
        qs = qs.filter(teachers=user)
    return qs.distinct()


def my_quizzes(user):
    qs = Quiz.objects.all()
    if not is_admin(user):
        qs = qs.filter(Q(created_by=user) | Q(course__teachers=user))
    return qs.distinct()


def get_course_or_403(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if not (is_admin(request.user) or course.teachers.filter(id=request.user.id).exists()):
        raise PermissionDenied("به این دوره دسترسی ندارید.")
    return course


def get_quiz_or_403(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)
    owner = quiz.created_by_id == request.user.id
    teaches = bool(quiz.course_id) and quiz.course.teachers.filter(id=request.user.id).exists()
    if not (is_admin(request.user) or owner or teaches):
        raise PermissionDenied("به این آزمون دسترسی ندارید.")
    return quiz


def _unique_slug(model, title, fallback):
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
    courses = my_courses(request.user)
    quizzes = my_quizzes(request.user)
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
    daily_map = {}
    for att in attempts.filter(completed_at__date__gte=start):
        if att.completed_at:
            d = timezone.localtime(att.completed_at).date()
            daily_map[d] = daily_map.get(d, 0) + 1
    daily_labels, daily_values = [], []
    for i in range(14):
        d = start + timedelta(days=i)
        daily_labels.append(d.strftime("%m/%d"))
        daily_values.append(daily_map.get(d, 0))

    # میانگین درصد به تفکیک آزمون (پربازدیدترین‌ها)
    per_quiz = (
        attempts.values("quiz__title")
        .annotate(avg=Avg("percentage"), c=Count("id"))
        .order_by("-c")[:8]
    )
    quiz_labels = [row["quiz__title"] for row in per_quiz]
    quiz_avg = [round(row["avg"] or 0, 1) for row in per_quiz]

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
    q = request.GET.get("q", "").strip()
    courses = my_courses(request.user).order_by("-created_at")
    if q:
        courses = courses.filter(title__icontains=q)
    return render(request, "panel/course_list.html", {"courses": courses, "q": q})


@staff_required
def course_create(request):
    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            if not course.slug:
                course.slug = _unique_slug(Course, course.title, "course")
            course.save()
            form.save_m2m()
            if not is_admin(request.user):
                course.teachers.add(request.user)
            messages.success(request, "دوره با موفقیت ساخته شد.")
            return redirect("panel:course_list")
    else:
        form = CourseForm()
    return render(request, "panel/course_form.html", {"form": form, "mode": "new"})


@staff_required
def course_edit(request, pk):
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
    course = get_course_or_403(request, pk)
    if request.method == "POST":
        course.delete()
        messages.success(request, "دوره حذف شد.")
    return redirect("panel:course_list")


@staff_required
def course_toggle_publish(request, pk):
    course = get_course_or_403(request, pk)
    if request.method == "POST":
        course.status = "draft" if course.status == "published" else "published"
        course.save(update_fields=["status"])
        messages.success(request, "وضعیت دوره تغییر کرد.")
    return redirect("panel:course_list")


# ============================ آزمون‌ها ============================
@staff_required
def quiz_list(request):
    quizzes = my_quizzes(request.user).select_related("course").order_by("-created_at")
    return render(request, "panel/quiz_list.html", {"quizzes": quizzes})


@staff_required
def quiz_create(request):
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
    quiz = get_quiz_or_403(request, pk)
    if request.method == "POST":
        quiz.delete()
        messages.success(request, "آزمون حذف شد.")
    return redirect("panel:quiz_list")


@staff_required
def quiz_toggle_publish(request, pk):
    quiz = get_quiz_or_403(request, pk)
    if request.method == "POST":
        quiz.is_published = not quiz.is_published
        quiz.save(update_fields=["is_published"])
        messages.success(request, "وضعیت آزمون تغییر کرد.")
    return redirect("panel:quiz_list")


@staff_required
def quiz_questions(request, pk):
    quiz = get_quiz_or_403(request, pk)
    qqs = quiz.quiz_questions.select_related("question").order_by("order", "id")
    return render(request, "panel/quiz_questions.html", {"quiz": quiz, "quiz_questions": qqs})


@staff_required
def question_add(request, pk):
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
    quiz = get_quiz_or_403(request, pk)
    if request.method == "POST":
        QuizQuestion.objects.filter(id=qq_id, quiz=quiz).delete()
        messages.success(request, "سوال از آزمون حذف شد.")
    return redirect("panel:quiz_questions", pk=quiz.pk)


# ============================ نتایج و نمرات ============================
@staff_required
def results(request):
    quizzes = (
        my_quizzes(request.user)
        .annotate(
            attempt_count=Count("attempts", filter=Q(attempts__status="completed")),
            avg_score=Avg("attempts__percentage", filter=Q(attempts__status="completed")),
        )
        .order_by("-attempt_count")
    )
    return render(request, "panel/results.html", {"quizzes": quizzes})


def _quiz_attempts(quiz):
    return quiz.attempts.filter(status="completed").select_related("student")


@staff_required
def quiz_results(request, pk):
    quiz = get_quiz_or_403(request, pk)
    attempts = _quiz_attempts(quiz).order_by("-percentage")
    total = attempts.count()
    passed = attempts.filter(is_passed=True).count()
    agg = attempts.aggregate(a=Avg("percentage"))
    stats = {
        "count": total,
        "passed": passed,
        "failed": total - passed,
        "avg": agg["a"] or 0,
    }
    return render(
        request,
        "panel/quiz_results.html",
        {"quiz": quiz, "attempts": attempts, "stats": stats},
    )


@staff_required
def quiz_results_csv(request, pk):
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
