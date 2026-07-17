"""نمایش و فیلتر تاریخچهٔ پرسش‌های هوش مصنوعی را در Django Admin پیکربندی می‌کند.

 
"""

from django.contrib import admin

from .models import AiQuestion


@admin.register(AiQuestion)
class AiQuestionAdmin(admin.ModelAdmin):
    """نحوهٔ نمایش، جست‌وجو و فیلتر AiQuestion را در پنل مدیریت تنظیم می‌کند."""
    list_display = ["user", "short_question", "status", "course", "response_ms", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["question", "answer", "user__username"]
    readonly_fields = ["created_at"]
    list_select_related = ["user", "course"]

    @admin.display(description="پرسش")
    def short_question(self, obj):
        """نسخهٔ کوتاه سؤال را برای ستون فهرست پنل مدیریت برمی‌گرداند."""
        return obj.question[:60]
