"""
پنل ادمین اپ کوییز.
نکته‌ی کلیدی: از inline استفاده می‌کنیم تا گزینه‌های یک سوال رو
همون صفحه‌ی سوال وارد کنیم، و سوالات یک آزمون رو همون جا مدیریت کنیم.
"""

from django.contrib import admin
from .models import (
    Topic,
    Question,
    Choice,
    Quiz,
    QuizQuestion,
    QuizAttempt,
    AttemptAnswer,
)


class ChoiceInline(admin.TabularInline):
    """گزینه‌ها رو داخل صفحه‌ی سوال وارد کن."""

    model = Choice
    extra = 4
    fields = ("text", "is_correct", "order")


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "order")
    list_filter = ("parent",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("short_text", "topic", "question_type", "difficulty", "points", "is_active")
    list_filter = ("question_type", "difficulty", "is_active", "topic")
    search_fields = ("text",)
    inlines = [ChoiceInline]
    list_editable = ("is_active",)
    autocomplete_fields = ("topic",)

    def short_text(self, obj):
        return obj.text[:60]

    short_text.short_description = "متن سوال"


class QuizQuestionInline(admin.TabularInline):
    """انتخاب سوالات برای آزمون با ترتیب."""

    model = QuizQuestion
    extra = 1
    autocomplete_fields = ("question",)


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "question_count", "total_points", "pass_mark", "is_published")
    list_filter = ("is_published", "course")
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}
    inlines = [QuizQuestionInline]
    list_editable = ("is_published",)


class AttemptAnswerInline(admin.TabularInline):
    model = AttemptAnswer
    extra = 0
    readonly_fields = ("question", "answer_text", "is_correct", "points_earned")
    can_delete = False


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("student", "quiz", "percentage", "is_passed", "status", "started_at")
    list_filter = ("status", "is_passed", "quiz")
    search_fields = ("student__username", "quiz__title")
    readonly_fields = ("score", "max_score", "percentage", "is_passed", "started_at", "completed_at")
    inlines = [AttemptAnswerInline]
