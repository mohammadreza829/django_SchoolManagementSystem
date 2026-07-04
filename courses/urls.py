# courses/urls.py

from django.urls import path
from . import views

app_name = "courses"

# نکته: از کانورتر داخلی جنگو یعنی str استفاده می‌کنیم.
# str هر رشته‌ای (از جمله فارسی) را قبول می‌کند و نیازی به کلاس یا ثبت کانورتر ندارد.

# ✅ فیکس: آدرس‌های ثابت (lesson/, download/) باید «قبل از» الگوهای slug بیایند.
# قبلاً `download/<id>/` هیچ‌وقت اجرا نمی‌شد چون الگوی دوبخشیِ
# `<course_slug>/<lesson_slug>/` آن را می‌بلعید و کاربر 404 می‌گرفت.
urlpatterns = [
    path("", views.course_list, name="course_list"),
    path("search/", views.search_courses, name="search"),
    path("my-courses/", views.my_courses, name="my_courses"),
    path("lesson/<int:lesson_id>/complete/", views.mark_lesson_complete, name="mark_lesson_complete"),
    path("lesson/<int:lesson_id>/comment/", views.add_comment, name="add_comment"),
    path("download/<int:attachment_id>/", views.download_attachment, name="download_attachment"),
    path("category/<str:slug>/", views.category_detail, name="category_detail"),
    path("<str:slug>/", views.course_detail, name="course_detail"),
    path("<str:course_slug>/enroll/", views.enroll_course, name="enroll_course"),
    path("<str:course_slug>/rate/", views.add_rating, name="add_rating"),
    path("<str:course_slug>/<str:lesson_slug>/", views.lesson_detail, name="lesson_detail"),
]
