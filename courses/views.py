# courses/views.py (نسخه ساده - بدون AJAX و API)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from .models import (
    Course,
    Category,
    Lesson,
    LessonProgress,
    LessonComment,
    LessonLike,
    LessonAttachment,
    CourseRating,
)
from accounts.models import User


def course_list(request):
    """
    صفحه لیست همه دوره‌ها
    """
    # گرفتن همه دوره‌های منتشر شده
    courses = Course.objects.filter(status="published")

    # فیلتر بر اساس دسته‌بندی
    category_slug = request.GET.get("category")
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        courses = courses.filter(category=category)

    # فیلتر بر اساس سطح
    level = request.GET.get("level")
    if level:
        courses = courses.filter(level=level)

    # جستجو
    search_query = request.GET.get("q")
    if search_query:
        courses = courses.filter(
            Q(title__icontains=search_query)
            | Q(short_description__icontains=search_query)
            | Q(teachers__first_name__icontains=search_query)
            | Q(teachers__last_name__icontains=search_query)
        ).distinct()

    # پیش‌بارگیری اساتید برای کاهش تعداد کوئری‌ها
    courses = courses.prefetch_related("teachers")

    # دسته‌بندی‌ها برای نمایش در فیلتر
    categories = Category.objects.filter(is_active=True)

    context = {
        "courses": courses,
        "categories": categories,
        "selected_category": category_slug,
        "selected_level": level,
        "search_query": search_query,
    }
    return render(request, "courses/course_list.html", context)


def course_detail(request, slug):
    """
    صفحه جزئیات یک دوره
    """
    course = get_object_or_404(Course, slug=slug, status="published")

    # افزایش تعداد بازدید
    course.view_count += 1
    course.save(update_fields=["view_count"])

    # گرفتن همه جلسات دوره به ترتیب
    lessons = course.lessons.all().order_by("order")

    # بررسی اینکه کاربر فعلی در این دوره ثبت‌نام کرده است یا نه
    is_enrolled = False
    lesson_progress = {}

    if request.user.is_authenticated:
        is_enrolled = course.students.filter(id=request.user.id).exists()

        # اگر ثبت‌نام کرده، پیشرفت هر جلسه را بگیر
        if is_enrolled:
            progresses = LessonProgress.objects.filter(
                lesson__in=lessons, user=request.user
            )
            for progress in progresses:
                lesson_progress[progress.lesson.id] = progress

    # جلسات پیش‌نمایش رایگان
    free_lessons = lessons.filter(is_free_preview=True)

    # دوره‌های مرتبط (همین دسته‌بندی)
    related_courses = Course.objects.filter(
        category=course.category, status="published"
    ).exclude(id=course.id)[:4]

    # امتیازات دوره
    ratings = course.ratings.select_related("user").order_by("-created_at")

    context = {
        "course": course,
        "lessons": lessons,
        "free_lessons": free_lessons,
        "is_enrolled": is_enrolled,
        "lesson_progress": lesson_progress,
        "related_courses": related_courses,
        "ratings": ratings,
    }
    return render(request, "courses/course_detail.html", context)


def lesson_detail(request, course_slug, lesson_slug):
    """
    صفحه تماشای جلسه آموزشی
    """
    course = get_object_or_404(Course, slug=course_slug)
    lesson = get_object_or_404(Lesson, course=course, slug=lesson_slug)

    # بررسی دسترسی کاربر
    can_access = False

    if lesson.is_free_preview:
        can_access = True
    elif request.user.is_authenticated:
        if (
            request.user.is_teacher
            or request.user.is_superuser
            or request.user.is_staff
        ):
            can_access = True
        elif course.students.filter(id=request.user.id).exists():
            can_access = True

    if not can_access:
        return redirect("courses:course_detail", slug=course_slug)

    # جلسات قبلی و بعدی
    all_lessons = list(course.lessons.all().order_by("order"))
    current_index = all_lessons.index(lesson)

    prev_lesson = all_lessons[current_index - 1] if current_index > 0 else None
    next_lesson = (
        all_lessons[current_index + 1] if current_index < len(all_lessons) - 1 else None
    )

    # گرفتن یا ساخت پیشرفت کاربر
    progress = None
    if request.user.is_authenticated:
        progress, created = LessonProgress.objects.get_or_create(
            lesson=lesson, user=request.user
        )

        # اگر کاربر برای اولین بار است، watch_count را افزایش بده
        if created:
            progress.watch_count = 1
            progress.save()

    # افزایش تعداد بازدید جلسه
    lesson.view_count += 1
    lesson.save(update_fields=["view_count"])

    # ضمیمه‌های جلسه
    attachments = lesson.attachments.all()

    # نظرات جلسه
    comments = lesson.comments.filter(is_approved=True, parent=None).select_related(
        "user"
    )

    context = {
        "course": course,
        "lesson": lesson,
        "prev_lesson": prev_lesson,
        "next_lesson": next_lesson,
        "progress": progress,
        "attachments": attachments,
        "comments": comments,
    }
    return render(request, "courses/lesson_detail.html", context)


@login_required
def enroll_course(request, course_slug):
    """
    ثبت‌نام در دوره
    """
    course = get_object_or_404(Course, slug=course_slug)

    # بررسی اینکه دوره منتشر شده باشد
    if course.status != "published":
        return redirect("courses:course_detail", slug=course_slug)

    # بررسی ظرفیت دوره (فیلد is_full اضافه شده به مدل)
    if course.is_full:
        return redirect("courses:course_detail", slug=course_slug)

    # بررسی مهلت ثبت‌نام (فیلد enrollment_deadline اضافه شده به مدل)
    if course.enrollment_deadline and course.enrollment_deadline < timezone.now():
        return redirect("courses:course_detail", slug=course_slug)

    # ثبت‌نام کاربر
    course.students.add(request.user)
    course.enroll_count = course.students.count()
    course.save(update_fields=["enroll_count"])

    return redirect("courses:course_detail", slug=course_slug)


@login_required
def mark_lesson_complete(request, lesson_id):
    """
    علامت زدن جلسه به عنوان دیده شده (با POST ساده)
    """
    if request.method != "POST":
        return redirect("home")

    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.course

    # بررسی دسترسی
    if not course.students.filter(id=request.user.id).exists():
        return redirect("courses:course_detail", slug=course.slug)

    # گرفتن یا ساخت پیشرفت
    progress, created = LessonProgress.objects.get_or_create(
        lesson=lesson, user=request.user
    )

    # علامت زدن به عنوان کامل
    if not progress.is_completed:
        progress.is_completed = True
        progress.completion_percentage = 100  # فیلد اضافه شده به مدل
        progress.completed_at = timezone.now()
        progress.save()

    # رفتن به جلسه بعدی اگر وجود دارد
    next_lesson = (
        course.lessons.filter(order__gt=lesson.order).order_by("order").first()
    )

    if next_lesson:
        return redirect(
            "courses:lesson_detail",
            course_slug=course.slug,
            lesson_slug=next_lesson.slug,
        )
    else:
        return redirect("courses:course_detail", slug=course.slug)


@login_required
def add_rating(request, course_slug):
    """
    افزودن امتیاز و نظر برای دوره (با فرم ساده POST)
    """
    course = get_object_or_404(Course, slug=course_slug)

    if request.method == "POST":
        score = request.POST.get("score")
        comment = request.POST.get("comment", "")

        if score:
            try:
                score = int(score)
                if 1 <= score <= 5:
                    # به‌روزرسانی یا ایجاد امتیاز
                    rating, created = CourseRating.objects.update_or_create(
                        course=course,
                        user=request.user,
                        defaults={"score": score, "comment": comment},
                    )
            except ValueError:
                pass

    return redirect("courses:course_detail", slug=course_slug)


@login_required
def add_comment(request, lesson_id):
    """
    افزودن نظر برای جلسه (با فرم ساده POST)
    """
    if request.method != "POST":
        return redirect("home")

    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.course

    # بررسی دسترسی
    if (
        not course.students.filter(id=request.user.id).exists()
        and not lesson.is_free_preview
    ):
        return redirect("courses:course_detail", slug=course.slug)

    comment_text = request.POST.get("comment", "").strip()

    if comment_text:
        # تصحیح شده: استفاده از text به جای comment
        comment = LessonComment.objects.create(
            lesson=lesson, user=request.user, text=comment_text
        )
        comment.is_approved = True
        comment.save()

        # به‌روزرسانی تعداد نظرات (فیلد comment_count اضافه شده به مدل Lesson)
        lesson.comment_count = lesson.comments.filter(is_approved=True).count()
        lesson.save(update_fields=["comment_count"])

    return redirect(
        "courses:lesson_detail", course_slug=course.slug, lesson_slug=lesson.slug
    )


@login_required
def download_attachment(request, attachment_id):
    """
    دانلود فایل ضمیمه جلسه
    """
    from django.http import HttpResponse
    import os

    attachment = get_object_or_404(LessonAttachment, id=attachment_id)
    lesson = attachment.lesson
    course = lesson.course

    # بررسی دسترسی
    can_download = False

    if attachment.is_free:
        can_download = True
    elif course.students.filter(id=request.user.id).exists():
        can_download = True
    elif request.user.is_teacher or request.user.is_superuser:
        can_download = True

    if not can_download:
        return redirect("courses:course_detail", slug=course.slug)

    # افزایش آمار دانلود
    attachment.download_count += 1
    attachment.save(update_fields=["download_count"])

    # ارسال فایل
    file_path = attachment.file.path
    file_name = os.path.basename(file_path)

    with open(file_path, "rb") as f:
        response = HttpResponse(f.read(), content_type="application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        return response


def category_detail(request, slug):
    """
    نمایش همه دوره‌های یک دسته‌بندی
    """
    category = get_object_or_404(Category, slug=slug, is_active=True)
    courses = Course.objects.filter(
        category=category, status="published"
    ).prefetch_related("teachers")

    context = {
        "category": category,
        "courses": courses,
    }
    return render(request, "courses/category_detail.html", context)


def search_courses(request):
    """
    صفحه جستجوی پیشرفته
    """
    query = request.GET.get("q", "").strip()
    courses = Course.objects.none()

    if query:
        courses = (
            Course.objects.filter(
                Q(title__icontains=query)
                | Q(short_description__icontains=query)
                | Q(description__icontains=query)
                | Q(teachers__first_name__icontains=query)
                | Q(teachers__last_name__icontains=query)
                | Q(category__name__icontains=query)
            )
            .filter(status="published")
            .distinct()
            .prefetch_related("teachers")
        )

    context = {
        "courses": courses,
        "query": query,
        "count": courses.count(),
    }
    return render(request, "courses/search_results.html", context)


# courses/views.py


@login_required
def my_courses(request):
    """دوره‌هایی که کاربر در آنها ثبت‌نام کرده"""
    courses = request.user.courses_enrolled.all().prefetch_related("teachers")

    # محاسبه پیشرفت هر دوره (اختیاری)
    for course in courses:
        total_lessons = course.lessons.count()
        completed_lessons = LessonProgress.objects.filter(
            lesson__course=course, user=request.user, is_completed=True
        ).count()
        course.progress_percentage = (
            int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0
        )
        course.completed_lessons = completed_lessons
        course.total_lessons_count = total_lessons

    context = {"courses": courses}
    return render(request, "courses/my_courses.html", context)
