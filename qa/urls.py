"""مسیر صفحهٔ ثبت سؤال و مشاهدهٔ تاریخچهٔ پاسخ‌های هوش مصنوعی را تعریف می‌کند.

 
"""

from django.urls import path
from . import views

app_name = "qa"

urlpatterns = [
    path("", views.ask_page, name="ask"),
]
