# courses/urls.py

from django.urls import path, register_converter
from . import views


class UnicodeSlugConverter:
    """مثل کانورتر slug پیش‌فرض جنگو، اما حروف یونیکد (فارسی) را هم می‌پذیرد."""

    regex = r"[-\w]+"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(UnicodeSlugConverter, "uslug")

app_name = "courses" 

urlpatterns = [
    path("", views.course_list, name="course_list"),
    path("search/", views.search_courses, name="search"),
    path("my-courses/", views.my_courses, name="my_courses"),  
    path("category/<uslug:slug>/", views.category_detail, name="category_detail"),
    path("<uslug:slug>/", views.course_detail, name="course_detail"),
    path("<uslug:course_slug>/enroll/", views.enroll_course, name="enroll_course"),
    path("<uslug:course_slug>/rate/", views.add_rating, name="add_rating"),
    path("<uslug:course_slug>/<uslug:lesson_slug>/",views.lesson_detail,name="lesson_detail",),
    path("lesson/<int:lesson_id>/complete/",views.mark_lesson_complete,name="mark_lesson_complete",),
    path("lesson/<int:lesson_id>/comment/", views.add_comment, name="add_comment"),
    path("download/<int:attachment_id>/",views.download_attachment,name="download_attachment",),
]
