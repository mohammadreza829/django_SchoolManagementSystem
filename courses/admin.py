# courses/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Course, Category, Lesson, LessonProgress, CourseRating, LessonAttachment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ['order', 'title', 'content_type', 'is_free_preview', 'duration_minutes']
    ordering = ['order']


class LessonProgressInline(admin.TabularInline):
    model = LessonProgress
    extra = 0
    readonly_fields = ['user', 'is_completed', 'completed_at']
    can_delete = False


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'get_teachers', 'level', 'price', 'status', 'enroll_count']
    list_filter = ['level', 'status']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['teachers', 'students']
    inlines = [LessonInline]
    readonly_fields = ['view_count', 'enroll_count', 'rating_avg']
    
    fieldsets = (
        ('اطلاعات اصلی', {'fields': ('title', 'slug', 'category', 'teachers', 'status', 'level')}),
        ('تصاویر', {'fields': ('thumbnail', 'cover_image')}),
        ('توضیحات', {'fields': ('short_description', 'description')}),
        ('قیمت', {'fields': ('price', 'discount_percent')}),
        ('آمار', {'fields': ('view_count', 'enroll_count', 'rating_avg')}),
    )
    
    def get_teachers(self, obj):
        return ", ".join([t.get_full_name() or t.username for t in obj.teachers.all()][:3])
    get_teachers.short_description = "اساتید"


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'content_type', 'is_free_preview']
    list_filter = ['course', 'content_type', 'is_free_preview']
    search_fields = ['title', 'course__title']
    inlines = [LessonProgressInline]


@admin.register(CourseRating)
class CourseRatingAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'score', 'created_at']
    list_filter = ['score', 'course']
    search_fields = ['user__username', 'course__title']


@admin.register(LessonAttachment)
class LessonAttachmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'lesson', 'is_free', 'download_count']
    list_filter = ['is_free', 'lesson']