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
    StudentSignUpForm,  # فرمی که برای دانش‌آموز ساختیم
    UserUpdateForm,
    ProfileUpdateForm,
    CustomPasswordChangeForm,
)

# چون مدل کاربر رو عوض کردیم، همیشه از این تابع استفاده می‌کنیم
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

    # چک کن که profile وجود داشته باشه
    if not hasattr(user_obj, "profile"):
        # اگه نداشت، بسازش (فقط برای امنیت)
        Profile.objects.create(user=user_obj)

    is_owner = request.user == user_obj

    context = {
        "user_obj": user_obj,
        "is_owner": is_owner,
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
            # بعد از تغییر پسورد، سشن کاربر از بین می‌رود، پس دوباره لاگین می‌کنیم
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
