from django.contrib import admin
from .models import Enrollment


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
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
