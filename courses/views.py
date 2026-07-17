"""صفحات دوره و جلسه و عملیات ثبت‌نام، پیشرفت، امتیاز، نظر، دانلود و جست‌وجو را مدیریت می‌کند.

این فایل بخشی از پروژهٔ مدرسهٔ آنلاین است و مسئولیت‌های آن عمداً در همین دامنه نگه داشته شده‌اند.
"""

# courses/views.py (نسخه ساده - بدون AJAX و API)

from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F
from django.utils import timezone
from .policies import can_rate_course, has_course_access as _has_course_access
from .services import (
    CourseServiceError,
    add_lesson_comment,
    enroll_student,
    mark_lesson_completed,
    set_course_rating,
)
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

    # ✅ فیکس: صفحه‌بندی واقعی + حفظ فیلترها در لینک صفحات
    # (قبلاً Paginator وجود نداشت و بلوک صفحه‌بندی تمپلیت هیچ‌وقت رندر نمی‌شد)
    courses = courses.order_by("-created_at")
    paginator = Paginator(courses, 9)
    page_obj = paginator.get_page(request.GET.get("page"))

    # پارامترهای فعلی (q, level, category) بدون page — برای لینک‌های صفحه‌بندی
    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = {
        "courses": page_obj.object_list,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "querystring": query_params.urlencode(),
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

    # افزایش تعداد بازدید (با F برای جلوگیری از race condition)
    course.view_count = F("view_count") + 1
    course.save(update_fields=["view_count"])
    course.refresh_from_db(fields=["view_count"])

    # گرفتن همه جلسات دوره به ترتیب
    lessons = course.lessons.all().order_by("order")

    # بررسی اینکه کاربر فعلی در این دوره ثبت‌نام کرده است یا نه
    is_enrolled = False
    lesson_progress = {}

    if request.user.is_authenticated:
        is_enrolled = _has_course_access(request.user, course)

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
    elif _has_course_access(request.user, course):
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

    # افزایش تعداد بازدید جلسه (با F برای جلوگیری از race condition)
    lesson.view_count = F("view_count") + 1
    lesson.save(update_fields=["view_count"])
    lesson.refresh_from_db(fields=["view_count"])

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
    """درخواست ثبت‌نام را به سرویس دامنه می‌سپارد و نتیجه را نمایش می‌دهد."""
    course = get_object_or_404(Course, slug=course_slug)
    if request.method != "POST":
        return redirect("courses:course_detail", slug=course_slug)

    try:
        result = enroll_student(student=request.user, course=course)
    except CourseServiceError as exc:
        messages.error(request, str(exc))
    else:
        if result.access_granted:
            messages.success(request, "ثبت‌نام انجام شد و دسترسی دوره فعال است ✅")
        else:
            messages.info(
                request,
                "ثبت‌نام اولیه انجام شد؛ دسترسی دورهٔ پولی پس از پرداخت فعال می‌شود.",
            )
    return redirect("courses:course_detail", slug=course_slug)


@login_required
def mark_lesson_complete(request, lesson_id):
    """پس از کنترل دسترسی، تکمیل جلسه را به سرویس پیشرفت واگذار می‌کند."""
    if request.method != "POST":
        return redirect("courses:course_list")

    lesson = get_object_or_404(Lesson.objects.select_related("course"), id=lesson_id)
    course = lesson.course
    if not _has_course_access(request.user, course):
        return redirect("courses:course_detail", slug=course.slug)

    mark_lesson_completed(user=request.user, lesson=lesson)
    next_lesson = course.lessons.filter(order__gt=lesson.order).order_by("order").first()
    if next_lesson:
        return redirect(
            "courses:lesson_detail",
            course_slug=course.slug,
            lesson_slug=next_lesson.slug,
        )
    return redirect("courses:course_detail", slug=course.slug)


@login_required
def add_rating(request, course_slug):
    """مجوز امتیازدهی را بررسی و ثبت امتیاز را به سرویس دامنه واگذار می‌کند."""
    course = get_object_or_404(Course, slug=course_slug, status="published")
    if not can_rate_course(request.user, course):
        messages.error(request, "برای امتیاز دادن باید ثبت‌نام فعال داشته باشید.")
        return redirect("courses:course_detail", slug=course_slug)
    if request.method != "POST":
        return redirect("courses:course_detail", slug=course_slug)

    try:
        _rating, created = set_course_rating(
            user=request.user,
            course=course,
            score=request.POST.get("score"),
            comment=request.POST.get("comment", ""),
        )
    except CourseServiceError as exc:
        messages.error(request, str(exc))
    else:
        action = "ثبت" if created else "به‌روزرسانی"
        messages.success(request, f"امتیازت با موفقیت {action} شد.")
    return redirect("courses:course_detail", slug=course_slug)


@login_required
def add_comment(request, lesson_id):
    """پس از کنترل دسترسی، ساخت نظر و شمارنده را به سرویس واگذار می‌کند."""
    if request.method != "POST":
        return redirect("courses:course_list")

    lesson = get_object_or_404(Lesson.objects.select_related("course"), id=lesson_id)
    course = lesson.course
    if not lesson.is_free_preview and not _has_course_access(request.user, course):
        return redirect("courses:course_detail", slug=course.slug)

    try:
        add_lesson_comment(
            user=request.user,
            lesson=lesson,
            text=request.POST.get("comment", ""),
        )
    except CourseServiceError as exc:
        messages.error(request, str(exc))
    return redirect(
        "courses:lesson_detail",
        course_slug=course.slug,
        lesson_slug=lesson.slug,
    )


@login_required
def download_attachment(request, attachment_id):
    """
    دانلود فایل ضمیمه جلسه
    """
    from django.http import FileResponse
    import os

    attachment = get_object_or_404(LessonAttachment, id=attachment_id)
    lesson = attachment.lesson
    course = lesson.course

    # بررسی دسترسی
    can_download = False

    if attachment.is_free:
        can_download = True
    elif _has_course_access(request.user, course):
        can_download = True

    if not can_download:
        return redirect("courses:course_detail", slug=course.slug)

    # افزایش آمار دانلود (با F برای جلوگیری از race condition)
    attachment.download_count = F("download_count") + 1
    attachment.save(update_fields=["download_count"])

    # ✅ فیکس: استریم فایل به جای خواندن کامل در حافظه
    # (قبلاً فایل‌های حجیم مثل ویدیو/PDF کل RAM سرور را اشغال می‌کردند)
    file_name = os.path.basename(attachment.file.name)
    return FileResponse(
        attachment.file.open("rb"), as_attachment=True, filename=file_name
    )


def category_detail(request, slug):
    """
    نمایش همه دوره‌های یک دسته‌بندی
    """
    category = get_object_or_404(Category, slug=slug, is_active=True)
    # دوره‌های خود دسته + دوره‌های همه‌ی زیردسته‌ها
    subcategory_ids = list(category.subcategories.values_list("id", flat=True))
    category_ids = [category.id] + subcategory_ids
    courses = Course.objects.filter(
        category_id__in=category_ids, status="published"
    ).prefetch_related("teachers").select_related("category")

    # فیلتر بر اساس سطح
    level = request.GET.get("level")
    if level:
        courses = courses.filter(level=level)

    # مرتب‌سازی
    sort = request.GET.get("sort", "newest")
    sort_map = {
        "newest": "-created_at",
        "popular": "-enroll_count",
        "cheapest": "price",
        "expensive": "-price",
    }
    courses = courses.order_by(sort_map.get(sort, "-created_at"))

    context = {
        "category": category,
        "courses": courses,
        "selected_level": level,
        "sort": sort,
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
