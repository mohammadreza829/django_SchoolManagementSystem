"""نمایش و مدیریت ثبت‌نام‌های دوره را در پنل مدیریت Django پیکربندی می‌کند.

این فایل بخشی از پروژهٔ مدرسهٔ آنلاین است و مسئولیت‌های آن عمداً در همین دامنه نگه داشته شده‌اند.
"""

from django.contrib import admin
from .models import Enrollment


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """نحوهٔ نمایش، جست‌وجو و فیلتر Enrollment را در پنل مدیریت تنظیم می‌کند."""
    list_display = (
        "student",
        "course",
        "status",
        "payment_status",
        "price_paid",
        "progress_percentage",
        "enrolled_at",
    )
    list_filter = ("status", "payment_status", "enrolled_at")
    search_fields = (
        "student__username",
        "student__first_name",
        "student__last_name",
        "course__title",
    )
    list_select_related = ("student", "course")
    readonly_fields = ("enrolled_at",)
    autocomplete_fields = ("student", "course")
    list_editable = ("status", "payment_status")
    ordering = ("-enrolled_at",)
