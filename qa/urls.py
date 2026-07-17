"""مسیر صفحهٔ ثبت سؤال و مشاهدهٔ تاریخچهٔ پاسخ‌های هوش مصنوعی را تعریف می‌کند.

این فایل بخشی از پروژهٔ مدرسهٔ آنلاین است و مسئولیت‌های آن عمداً در همین دامنه نگه داشته شده‌اند.
"""

from django.urls import path
from . import views

app_name = "qa"

urlpatterns = [
    path("", views.ask_page, name="ask"),
]
