"""نمایش تراکنش‌های پرداخت در پنل مدیریت (فقط‌خواندنی)."""

from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "course", "amount", "status", "ref_id", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("authority", "ref_id", "user__username", "course__title")
    readonly_fields = (
        "user", "course", "enrollment", "amount",
        "authority", "ref_id", "status", "created_at", "updated_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False
