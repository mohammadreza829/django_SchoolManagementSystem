# accounts/urls.py

from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # مسیرهای قبلی
    path("signup/", views.register, name="student_signup"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("profile/<str:username>/", views.profile_view, name="profile_detail"),
    path("password/change/", views.change_password, name="change_password"),
    path("notifications/", views.notifications_view, name="notifications"),
    path("users/", views.user_list, name="user_list"),
    # مسیر جدید برای داشبورد
    path("dashboard/", views.dashboard_view, name="dashboard"), # <--- این خط را اضافه کنید

]
