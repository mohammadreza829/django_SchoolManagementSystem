from django.contrib import admin
from .models import CourseMessage


@admin.register(CourseMessage)
class CourseMessageAdmin(admin.ModelAdmin):
    list_display = ("course", "sender", "is_announcement", "created_at")
    list_filter = ("is_announcement", "created_at", "course")
    search_fields = ("text",)
    autocomplete_fields = ()
