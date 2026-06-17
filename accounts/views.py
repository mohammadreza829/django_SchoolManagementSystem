from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.forms import AuthenticationForm
from django.db import models
from .models import Profile, Notification
from .forms import (
    StudentSignUpForm,  
    UserUpdateForm,
    ProfileUpdateForm,
    CustomPasswordChangeForm,
)


try:
    from courses.models import Course

    COURSES_AVAILABLE = True
except ImportError:
    COURSES_AVAILABLE = False

User = get_user_model()


# ==================== ۱. ثبت‌نام دانش‌آموز ====================
def register(request):
    """ثبت‌نام دانش‌آموز جدید"""
    if request.user.is_authenticated:
        messages.info(request, "شما قبلاً وارد شده‌اید.")
        return redirect("accounts:profile")

    if request.method == "POST":
        form = StudentSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()  # مستقیماً save کن
            login(request, user)
            messages.success(request, f"خوش آمدی {user.first_name}!")
            return redirect("accounts:profile")
    else:
        form = StudentSignUpForm()

    return render(request, "accounts/register.html", {"form": form})


# ==================== ۲. ورود و خروج ====================
def user_login(request):
    """ورود کاربر به سایت"""
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(
                request, f"خوش آمدید {user.get_full_name() or user.username}!"
            )
            next_url = request.GET.get("next")
            return redirect(next_url or "accounts:profile")  # تغییر این خط
        else:
            messages.error(request, "نام کاربری یا رمز عبور اشتباه است.")
    else:
        form = AuthenticationForm()

    return render(request, "accounts/login.html", {"form": form})


@login_required
def user_logout(request):
    """خروج از حساب کاربری"""
    logout(request)
    messages.success(request, "با موفقیت خارج شدید. به امید دیدار مجدد!")
    return redirect("accounts:login")


# ==================== ۳. مدیریت پروفایل ====================
@login_required
def profile_view(request, username=None):
    if username:
        user_obj = get_object_or_404(User, username=username)
    else:
        user_obj = request.user

    if not hasattr(user_obj, "profile"):
        Profile.objects.create(user=user_obj)

    is_owner = request.user == user_obj

    # ========== اضافه کردن دوره‌ها ==========
    teaching_courses = []
    enrolled_courses = []

    if COURSES_AVAILABLE:
        if user_obj.is_teacher:
            teaching_courses = Course.objects.filter(
                teachers=user_obj, status="published"
            ).order_by("-created_at")[:6]

        if user_obj.is_student:
            enrolled_courses = user_obj.courses_enrolled.filter(
                status="published"
            ).order_by("-created_at")[:6]

    context = {
        "user_obj": user_obj,
        "is_owner": is_owner,
        "teaching_courses": teaching_courses,
        "enrolled_courses": enrolled_courses,
    }
    return render(request, "accounts/profile.html", context)


@login_required
def edit_profile(request):
    # اگه profile وجود نداشت بساز
    if not hasattr(request.user, "profile"):
        Profile.objects.create(user=request.user)

    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(
            request.POST, request.FILES, instance=request.user.profile
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "تغییرات با موفقیت ذخیره شد.")
            return redirect("accounts:profile")  # هدایت به پروفایل شخصی
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    return render(
        request,
        "accounts/edit_profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
        },
    )


@login_required
def change_password(request):
    """تغییر رمز عبور کاربر"""
    if request.method == "POST":
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "رمز عبور شما با موفقیت تغییر کرد.")
            return redirect("accounts:profile")
    else:
        form = CustomPasswordChangeForm(request.user)

    return render(request, "accounts/change_password.html", {"form": form})


# ==================== ۴. مدیریت اعلان‌ها و لیست کاربران ====================
@login_required
def notifications_view(request):
    notes = request.user.notifications.all()
    notes.filter(is_read=False).update(is_read=True)
    return render(request, "accounts/notifications.html", {"notes": notes})


from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def user_list(request):
    """لیست اساتید یا کاربران (فقط برای کارمندان سایت)"""
    users = User.objects.filter(is_active=True).order_by("-date_joined")

    query = request.GET.get("q")
    if query:
        users = users.filter(
            models.Q(username__icontains=query)
            | models.Q(first_name__icontains=query)
            | models.Q(last_name__icontains=query)
        )

    paginator = Paginator(users, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "accounts/user_list.html", {"page_obj": page_obj})

# ==================== ۵. داشبورد ====================
@login_required
def dashboard_view(request):
    from django.db.models import Sum

    user = request.user

    # مقادیر پیش‌فرض
    active_courses = []
    teaching_courses_count = 0
    enrolled_courses_count = 0
    total_notifications = user.notifications.filter(is_read=False).count()
    recent_courses = []
    completed_courses = []
    total_hours = 0
    avg_progress = 0
    recent_activities = []

    if COURSES_AVAILABLE:
        from courses.models import LessonProgress

        if user.is_teacher:
            teaching_courses_count = Course.objects.filter(
                teachers=user, status="published"
            ).count()

        # دوره‌های ثبت‌نام‌شده‌ی کاربر برای هر نقشی نمایش داده می‌شوند
        active_courses = list(
            user.courses_enrolled.all().prefetch_related("teachers", "lessons")
        )
        enrolled_courses_count = len(active_courses)

        # محاسبه‌ی واقعی پیشرفت هر دوره از روی جلسه‌های تکمیل‌شده
        progress_sum = 0
        total_minutes = 0
        for course in active_courses:
            total_lessons = course.lessons.count()
            completed_lessons = LessonProgress.objects.filter(
                lesson__course=course, user=user, is_completed=True
            ).count()
            prog = int((completed_lessons / total_lessons) * 100) if total_lessons else 0
            course.user_progress = prog
            course.completed_lessons = completed_lessons
            course.total_lessons_count = total_lessons
            progress_sum += prog
            if total_lessons > 0 and prog >= 100:
                completed_courses.append(course)
            watched = (
                LessonProgress.objects.filter(
                    lesson__course=course, user=user, is_completed=True
                ).aggregate(m=Sum("lesson__duration_minutes"))["m"]
                or 0
            )
            total_minutes += watched

        if active_courses:
            avg_progress = int(progress_sum / len(active_courses))

        total_hours = round(total_minutes / 60, 1)
        if total_hours == int(total_hours):
            total_hours = int(total_hours)

        # فعالیت‌های اخیر بر اساس آخرین جلسه‌های دیده‌شده
        recent_progress = (
            LessonProgress.objects.filter(user=user)
            .select_related("lesson", "lesson__course")
            .order_by("-last_watched")[:5]
        )
        for lp in recent_progress:
            recent_activities.append(
                {
                    "title": lp.lesson.course.title + " — " + lp.lesson.title,
                    "date": "تکمیل شده" if lp.is_completed else "در حال مطالعه",
                }
            )

        recent_courses = Course.objects.filter(
            status="published"
        ).order_by("-created_at")[:3]

    context = {
        "active_courses": active_courses,
        "enrolled_courses_count": enrolled_courses_count,
        "teaching_courses_count": teaching_courses_count,
        "total_notifications": total_notifications,
        "completed_courses": completed_courses,
        "total_hours": total_hours,
        "avg_progress": avg_progress,
        "recent_activities": recent_activities,
        "recent_courses": recent_courses,
    }

    return render(request, "accounts/dashboard.html", context)


# ==================== صفحه اصلی (لندینگ پیج) ====================
def home(request):
    """صفحه اصلی سایت با معرفی دوره‌ها و آزمون‌ها"""
    featured_courses = []
    try:
        from courses.models import Course
        featured_courses = list(Course.objects.filter(status="published")[:6])
    except Exception:
        pass

    context = {"featured_courses": featured_courses}
    return render(request, "home.html", context)
