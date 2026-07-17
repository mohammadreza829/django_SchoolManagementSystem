"""نمایش و فیلتر پیام‌های دوره را در Django Admin پیکربندی می‌کند.

 
"""

from django.contrib import admin
from .models import CourseMessage


@admin.register(CourseMessage)
class CourseMessageAdmin(admin.ModelAdmin):
    """نحوهٔ نمایش، جست‌وجو و فیلتر CourseMessage را در پنل مدیریت تنظیم می‌کند."""
    list_display = ("course", "sender", "is_announcement", "created_at")
    list_filter = ("is_announcement", "created_at", "course")
    search_fields = ("text",)
    autocomplete_fields = ()
