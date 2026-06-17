# quiz/urls.py
from django.urls import path
from . import views

app_name = "quiz"

urlpatterns = [
    # لیست همه‌ی آزمون‌ها
    path("", views.quiz_list, name="quiz_list"),
    # صفحه‌ی نمودار پیشرفت دانش‌آموز (قبل از slug تا تداخل نشه)
    path("my-progress/", views.my_progress, name="my_progress"),
    # صفحه‌ی معرفی آزمون (قبل از شروع)
    path("<slug:slug>/", views.quiz_detail, name="quiz_detail"),
    # صفحه‌ی دادن آزمون (GET فرم رو نشون می‌ده، POST تصحیح می‌کنه)
    path("<slug:slug>/take/", views.take_quiz, name="take_quiz"),
    # صفحه‌ی نتیجه‌ی یک تلاش
    path("attempt/<int:attempt_id>/result/", views.quiz_result, name="quiz_result"),
]
