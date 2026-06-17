# panel/urls.py
from django.urls import path

from . import views

app_name = "panel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # دوره‌ها
    path("courses/", views.course_list, name="course_list"),
    path("courses/new/", views.course_create, name="course_create"),
    path("courses/<int:pk>/edit/", views.course_edit, name="course_edit"),
    path("courses/<int:pk>/delete/", views.course_delete, name="course_delete"),
    path("courses/<int:pk>/toggle/", views.course_toggle_publish, name="course_toggle"),
    # آزمون‌ها
    path("quizzes/", views.quiz_list, name="quiz_list"),
    path("quizzes/new/", views.quiz_create, name="quiz_create"),
    path("quizzes/<int:pk>/edit/", views.quiz_edit, name="quiz_edit"),
    path("quizzes/<int:pk>/delete/", views.quiz_delete, name="quiz_delete"),
    path("quizzes/<int:pk>/toggle/", views.quiz_toggle_publish, name="quiz_toggle"),
    path("quizzes/<int:pk>/questions/", views.quiz_questions, name="quiz_questions"),
    path("quizzes/<int:pk>/questions/add/", views.question_add, name="question_add"),
    path("quizzes/<int:pk>/questions/<int:qq_id>/remove/", views.question_remove, name="question_remove"),
    # نتایج و نمرات
    path("results/", views.results, name="results"),
    path("results/<int:pk>/", views.quiz_results, name="quiz_results"),
    path("results/<int:pk>/csv/", views.quiz_results_csv, name="quiz_results_csv"),
    path("attempt/<int:attempt_id>/", views.attempt_detail, name="attempt_detail"),
]
