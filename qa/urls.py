from django.urls import path
from . import views

app_name = "qa"

urlpatterns = [
    path("", views.ask_page, name="ask"),
]
