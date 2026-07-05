from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.forms import AuthenticationForm
from django.db import models
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.contrib.auth import views as auth_views
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
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
            # ✅ فیکس: تأیید ایمیل — حساب تا کلیک روی لینک فعال‌سازی غیرفعال می‌ماند
            # (قبلاً هر ایمیل جعلی‌ای بدون تأیید پذیرفته می‌شد)
            user = form.save()
            user.is_active = False
            user.save(update_fields=["is_active"])
            _send_activation_email(request, user)
            # حالت توسعه: چون سرور ایمیل واقعی تنظیم نشده، لینک فعال‌سازی در صفحه‌ی ورود هم نمایش داده می‌شود
            if django_settings.DEBUG and _email_is_console():
                request.session["dev_activation_link"] = _build_activation_link(request, user)
            messages.success(
                request,
                "حسابت ساخته شد! لینک فعال‌سازی به ایمیلت ارسال شد؛ بعد از تأیید می‌تونی وارد بشی.",
            )
            return redirect("accounts:login")
    else:
        form = StudentSignUpForm()

    return render(request, "accounts/register.html", {"form": form})


def _email_is_console():
    """اگر بک‌اند ایمیل «کنسولی» باشد یعنی سرور ایمیل واقعی نداریم (حالت توسعه)."""
    return "console" in str(getattr(django_settings, "EMAIL_BACKEND", ""))


def _build_activation_link(request, user):
    """لینک فعال‌سازی حساب را می‌سازد."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return request.build_absolute_uri(
        reverse("accounts:activate", kwargs=dict(uidb64=uid, token=token))
    )


def _send_activation_email(request, user):
    """لینک فعال‌سازی حساب را برای کاربر ایمیل می‌کند."""
    link = _build_activation_link(request, user)
    send_mail(
        subject="فعال‌سازی حساب مکتب‌پلاس",
        message=(
            "سلام " + (user.first_name or user.username) + "!\n\n"
            "برای فعال‌سازی حسابت در مکتب‌پلاس روی لینک زیر کلیک کن:\n"
            + link + "\n\n"
            "اگر تو ثبت‌نام نکرده‌ای، این ایمیل را نادیده بگیر."
        ),
        from_email=None,
        recipient_list=[user.email],
        fail_silently=False,
    )


def activate(request, uidb64, token):
    """فعال‌سازی حساب از طریق لینک ایمیل"""
    UserModel = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = UserModel.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
        messages.success(request, "ایمیلت تأیید شد! حالا می‌تونی وارد بشی.")
        return redirect("accounts:login")

    messages.error(request, "لینک فعال‌سازی نامعتبر یا منقضی است.")
    return redirect("accounts:login")


# ==================== بازیابی رمز عبور ====================
class MaktabPasswordResetView(auth_views.PasswordResetView):
    """فرم «فراموشی رمز» — در حالت توسعه، لینک بازیابی در صفحه‌ی بعد هم نمایش داده می‌شود."""

    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")

    def form_valid(self, form):
        response = super().form_valid(form)
        if django_settings.DEBUG and _email_is_console():
            email = form.cleaned_data["email"]
            links = []
            for user in form.get_users(email):
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                links.append(
                    self.request.build_absolute_uri(
                        reverse(
                            "accounts:password_reset_confirm",
                            kwargs=dict(uidb64=uid, token=token),
                        )
                    )
                )
            self.request.session["dev_reset_links"] = links
            self.request.session["dev_reset_email"] = email
        return response


def password_reset_done(request):
    """صفحه‌ی «ایمیل ارسال شد» — در حالت توسعه لینک را هم نشان می‌دهد."""
    context = dict(dev_reset_links=None, dev_reset_email=None)
    if django_settings.DEBUG and _email_is_console():
        context["dev_reset_links"] = request.session.pop("dev_reset_links", None)
        context["dev_reset_email"] = request.session.pop("dev_reset_email", None)
    return render(request, "accounts/password_reset_done.html", context)


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
            # ✅ فیکس امنیتی (Open Redirect): پارامتر next باید اعتبارسنجی شود،
            # وگرنه مهاجم می‌تواند کاربر را بعد از لاگین به سایت فیشینگ بفرستد
            # (مثلاً /accounts/login/?next=https://evil.com)
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("accounts:profile")
        else:
            # ✅ فیکس: اگر حساب هنوز فعال نشده، پیام درست نمایش بده (نه «رمز اشتباه است»)
            username = (request.POST.get("username") or "").strip()
            UserModel = get_user_model()
            inactive_user = (
                UserModel.objects.filter(username=username, is_active=False).first()
                if username
                else None
            )
            if inactive_user:
                messages.warning(
                    request,
                    "حسابت هنوز فعال نشده! لینک فعال‌سازی داخل ایمیلت را باز کن.",
                )
                # حالت توسعه: لینک فعال‌سازی را همین‌جا در صفحه‌ی ورود نشان بده
                if django_settings.DEBUG and _email_is_console():
                    request.session["dev_activation_link"] = _build_activation_link(
                        request, inactive_user
                    )
            else:
                messages.error(request, "نام کاربری یا رمز عبور اشتباه است.")
    else:
        form = AuthenticationForm()

    return render(
        request,
        "accounts/login.html",
        dict(
            form=form,
            dev_activation_link=request.session.pop("dev_activation_link", None),
        ),
    )


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
    qs = request.user.notifications.all()
    # وضعیت خوانده/نخوانده را برای نمایش همین صفحه نگه می‌داریم (snapshot)
    notes = list(qs)
    # سپس همه‌ی اعلان‌های نخوانده را خوانده‌شده علامت می‌زنیم تا شمارنده‌ی زنگوله صفر شود
    qs.filter(is_read=False).update(is_read=True)
    return render(request, "accounts/notifications.html", {"notifications": notes})


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

        # دوره‌های ثبت‌نام‌شده‌ی کاربر برای هر نقشی نمایش داده می‌شو��د
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
