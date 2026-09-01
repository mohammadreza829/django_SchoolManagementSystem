"""مسیرهای شروع و بازگشت پرداخت زرین‌پال."""

from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("callback/", views.callback, name="callback"),
    path("<str:course_slug>/start/", views.start, name="start"),
]
