"""صفحات دوره و جلسه و عملیات ثبت‌نام، پیشرفت، امتیاز، نظر، دانلود و جست‌وجو را مدیریت می‌کند.

این فایل بخشی از پروژهٔ مدرسهٔ آنلاین است و مسئولیت‌های آن عمداً در همین دامنه نگه داشته شده‌اند.
قواعد کسب‌وکار در `services.py` و مجوزها در `policies.py` هستند؛ اینجا فقط
ورودی HTTP، انتخاب داده برای تمپلیت و پیام کاربر مدیریت می‌شود.
"""

import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render

from Enrollment.models import Enrollment

from .models import (
    Category,
    Course,
    Lesson,
    LessonAttachment,
    LessonProgress,
)
from .policies import can_rate_course, has_course_access as _has_course_access
from .services import (
    CourseServiceError,
    add_lesson_comment,
    confirm_enrollment_payment,
    enroll_student,
    mark_lesson_completed,
    set_course_rating,
)

COURSES_PER_PAGE = 9


def _get_enrollment(user, course):
    """ثبت‌نام غیرلغوشدهٔ کاربر در دوره را برمی‌گرداند (یا None)."""
    if not user.is_authenticated:
        return None
    return (
        Enrollment.objects.filter(student=user, course=course)
        .exclude(status="cancelled")
        .first()
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

    # پیش‌بارگیری اساتید و دسته برای کاهش تعداد کوئری‌ها
    courses = courses.select_related("category").prefetch_related("teachers")

    # دسته‌بندی‌ها برای نمایش در فیلتر
    categories = Category.objects.filter(is_active=True)

    # ✅ فیکس: صفحه‌بندی واقعی + حفظ فیلترها در لینک صفحات
    # (قبلاً Paginator وجود نداشت و بلوک صفحه‌بندی تمپلیت هیچ‌وقت رندر نمی‌شد)
    courses = courses.order_by("-created_at")
    paginator = Paginator(courses, COURSES_PER_PAGE)
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
    Course.objects.filter(pk=course.pk).update(view_count=F("view_count") + 1)
    course.refresh_from_db(fields=["view_count"])

    # گرفتن همه جلسات دوره به ترتیب
    lessons = course.lessons.all().order_by("order")

    # بررسی اینکه کاربر فعلی به محتوای دوره دسترسی دارد یا نه
    is_enrolled = False
    lesson_progress = {}
    enrollment = None

    if request.user.is_authenticated:
        is_enrolled = _has_course_access(request.user, course)
        enrollment = _get_enrollment(request.user, course)

        # اگر دسترسی دارد، پیشرفت هر جلسه را یک‌جا بگیر (بدون کوئری در حلقه)
        if is_enrolled:
            progresses = LessonProgress.objects.filter(
                lesson__course=course, user=request.user
            )
            lesson_progress = {
                progress.lesson_id: progress for progress in progresses
            }

    # ✅ فیکس: وقتی ثبت‌نام انجام شده ولی پرداخت pending است، دوره باز نمی‌شد
    # و هیچ راهی به کاربر نشان داده نمی‌شد. این پرچم دکمهٔ «تکمیل پرداخت» را فعال می‌کند.
    payment_pending = bool(enrollment and enrollment.payment_status == "pending")

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
        "enrollment": enrollment,
        "payment_pending": payment_pending,
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
    has_access = _has_course_access(request.user, course)
    if not lesson.is_free_preview and not has_access:
        return redirect("courses:course_detail", slug=course_slug)

    # ✅ فیکس: جلسهٔ قبلی/بعدی با کوئری روی order محاسبه می‌شود.
    # (قبلاً list.index استفاده می‌شد که برای جلسهٔ حذف‌شده از لیست ValueError می‌داد)
    prev_lesson = (
        course.lessons.filter(order__lt=lesson.order).order_by("-order").first()
    )
    next_lesson = (
        course.lessons.filter(order__gt=lesson.order).order_by("order").first()
    )

    # گرفتن یا ساخت پیشرفت کاربر
    progress = None
    completed_lesson_ids = []
    if request.user.is_authenticated:
        progress, created = LessonProgress.objects.get_or_create(
            lesson=lesson,
            user=request.user,
            defaults={"watch_count": 1},
        )
        # ✅ فیکس: watch_count در بازدیدهای بعدی هم بالا می‌رود (قبلاً فقط بار اول ۱ می‌شد)
        if not created:
            LessonProgress.objects.filter(pk=progress.pk).update(
                watch_count=F("watch_count") + 1
            )
            progress.refresh_from_db(fields=["watch_count"])

        # ✅ بهبود: جلسات تکمیل‌شده در یک کوئری تا سایدبار بتواند تیک نشان دهد
        completed_lesson_ids = list(
            LessonProgress.objects.filter(
                lesson__course=course, user=request.user, is_completed=True
            ).values_list("lesson_id", flat=True)
        )

    # افزایش تعداد بازدید جلسه (با F برای جلوگیری از race condition)
    Lesson.objects.filter(pk=lesson.pk).update(view_count=F("view_count") + 1)
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
        "lessons": course.lessons.all().order_by("order"),
        "has_access": has_access,
        "completed_lesson_ids": completed_lesson_ids,
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
            # ✅ فیکس: قبلاً کاربر فقط یک پیام می‌دید و دوره برایش باز نمی‌شد؛
            # اکنون به صفحهٔ تأیید پرداخت هدایت می‌شود تا دسترسی کامل شود.
            messages.info(
                request,
                "ثبت‌نام اولیه انجام شد؛ برای باز شدن کامل دوره پرداخت را تأیید کن.",
            )
            return redirect("courses:checkout", course_slug=course_slug)
    return redirect("courses:course_detail", slug=course_slug)


@login_required
def checkout(request, course_slug):
    """صفحهٔ تأیید پرداخت دورهٔ پولی و باز کردن دسترسی کامل.

تا زمان اتصال درگاه واقعی، این صفحه نقش تأییدیهٔ پرداخت را دارد.
"""
    course = get_object_or_404(Course, slug=course_slug, status="published")
    enrollment = _get_enrollment(request.user, course)

    if enrollment is None:
        messages.info(request, "اول در این دوره ثبت‌نام کن.")
        return redirect("courses:course_detail", slug=course_slug)

    if enrollment.payment_status in ("free", "paid"):
        messages.info(request, "دسترسی این دوره از قبل فعال است.")
        return redirect("courses:course_detail", slug=course_slug)

    if request.method == "POST":
        try:
            confirm_enrollment_payment(student=request.user, course=course)
        except CourseServiceError as exc:
            messages.error(request, str(exc))
            return redirect("courses:checkout", course_slug=course_slug)
        messages.success(request, "پرداخت تأیید شد و دوره کامل باز شد ✅")
        return redirect("courses:course_detail", slug=course_slug)

    first_lesson = course.lessons.all().order_by("order").first()
    context = {
        "course": course,
        "enrollment": enrollment,
        "first_lesson": first_lesson,
        "total_lessons_count": course.lessons.count(),
    }
    return render(request, "courses/checkout.html", context)


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
    else:
        messages.success(request, "دیدگاهت ثبت شد.")
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
    attachment = get_object_or_404(
        LessonAttachment.objects.select_related("lesson__course"), id=attachment_id
    )
    course = attachment.lesson.course

    # بررسی دسترسی
    if not attachment.is_free and not _has_course_access(request.user, course):
        return redirect("courses:course_detail", slug=course.slug)

    # افزایش آمار دانلود (با F برای جلوگیری از race condition)
    LessonAttachment.objects.filter(pk=attachment.pk).update(
        download_count=F("download_count") + 1
    )

    # ✅ فیکس: استریم فایل به جای خواندن کامل در حافطه
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
    courses = (
        Course.objects.filter(category_id__in=category_ids, status="published")
        .select_related("category")
        .prefetch_related("teachers")
    )

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

    # ✅ فیکس: این صفحه هم صفحه‌بندی می‌شود تا دسته‌های پرحجم کل دیتابیس را رندر نکنند
    paginator = Paginator(courses, COURSES_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = {
        "category": category,
        "courses": page_obj.object_list,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "querystring": query_params.urlencode(),
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
            .select_related("category")
            .prefetch_related("teachers")
            .order_by("-created_at")
        )

    # ✅ فیکس: صفحه‌بندی نتایج جست‌وجو + شمارش با paginator
    # (قبلاً هم کل نتایج رندر می‌شد و هم count یک کوئری اضافه می‌زد)
    paginator = Paginator(courses, COURSES_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = {
        "courses": page_obj.object_list,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "querystring": query_params.urlencode(),
        "query": query,
        "count": paginator.count,
    }
    return render(request, "courses/search_results.html", context)


@login_required
def my_courses(request):
    """دوره‌هایی که کاربر در آن‌ها ثبت‌نام فعال دارد، همراه با درصد پیشرفت."""
    # ✅ فیکس: حذف N+1 — قبلاً برای هر دوره دو کوئری جدا در حلقه زده می‌شد.
    # اکنون همهٔ شمارش‌ها در یک کوئری با annotate انجام می‌شود و لغوشده‌ها هم
    # دیگر در «دوره‌های من» نمایش داده نمی‌شوند.
    courses = (
        Course.objects.filter(
            enrollments__student=request.user,
            enrollments__status__in=("active", "completed"),
        )
        .select_related("category")
        .prefetch_related("teachers")
        .annotate(
            total_lessons_count=Count("lessons", distinct=True),
            completed_lessons=Count(
                "lessons__progresses",
                distinct=True,
                filter=Q(
                    lessons__progresses__user=request.user,
                    lessons__progresses__is_completed=True,
                ),
            ),
        )
        .distinct()
        .order_by("-created_at")
    )

    # محاسبهٔ درصد پیشرفت در پایتون؛ هیچ کوئری اضافه‌ای نمی‌زند.
    course_list_with_progress = list(courses)
    for course in course_list_with_progress:
        total = course.total_lessons_count
        course.progress_percentage = (
            int(course.completed_lessons / total * 100) if total else 0
        )

    context = {"courses": course_list_with_progress}
    return render(request, "courses/my_courses.html", context)
