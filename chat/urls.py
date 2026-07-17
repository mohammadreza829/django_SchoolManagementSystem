"""مسیرهای اتاق چت، دریافت پیام، ارسال پیام و حذف پیام را تعریف می‌کند.

 
"""

from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("<int:course_id>/", views.course_chat, name="room"),
    path("<int:course_id>/messages/", views.messages_json, name="messages"),
    path("<int:course_id>/send/", views.post_message, name="send"),
    path("<int:course_id>/delete/<int:message_id>/", views.delete_message, name="delete"),
]
