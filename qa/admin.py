from django.contrib import admin

from .models import AiQuestion


@admin.register(AiQuestion)
class AiQuestionAdmin(admin.ModelAdmin):
    list_display = ["user", "short_question", "status", "course", "response_ms", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["question", "answer", "user__username"]
    readonly_fields = ["created_at"]
    list_select_related = ["user", "course"]

    @admin.display(description="پرسش")
    def short_question(self, obj):
        return obj.question[:60]
