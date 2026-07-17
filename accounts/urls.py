"""مسیرهای ثبت‌نام، ورود، بازیابی رمز، پروفایل، اعلان‌ها و داشبورد کاربر را تعریف می‌کند.

 
"""

from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.register, name="student_signup"),
    # ✅ فیکس: فعال‌سازی حساب با لینک ایمیل
    path("activate/<uidb64>/<token>/", views.activate, name="activate"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    # ✅ فیکس: بازیابی رمز عبور (فراموشی رمز) — قبلاً اصلاً وجود نداشت
    path(
        "password/reset/",
        # نسخه‌ی سفارشی: در حالت توسعه لینک بازیابی را در صفحه‌ی بعد هم نشان می‌دهد
        views.MaktabPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password/reset/done/",
        views.password_reset_done,
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("profile/<str:username>/", views.profile_view, name="profile_detail"),
    path("password/change/", views.change_password, name="change_password"),
    path("notifications/", views.notifications_view, name="notifications"),
    path("users/", views.user_list, name="user_list"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
]
