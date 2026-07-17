"""مدیریت دسته‌ها، دوره‌ها، جلسات، پیشرفت، امتیاز و ضمیمه‌ها را در Django Admin پیکربندی می‌کند.

این فایل بخشی از پروژهٔ مدرسهٔ آنلاین است و مسئولیت‌های آن عمداً در همین دامنه نگه داشته شده‌اند.
"""

# courses/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .services import synchronize_course_rating_stats
from .models import Course, Category, Lesson, LessonProgress, CourseRating, LessonAttachment
from Enrollment.models import Enrollment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """نحوهٔ نمایش، جست‌وجو و فیلتر Category را در پنل مدیریت تنظیم می‌کند."""
    list_display = ['name', 'parent', 'order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']


class LessonInline(admin.TabularInline):
    """نمایش و ویرایش رکوردهای مرتبط را به‌صورت درون‌خطی در پنل مدیریت فراهم می‌کند."""
    model = Lesson
    extra = 1
    fields = ['order', 'title', 'content_type', 'is_free_preview', 'duration_minutes']
    ordering = ['order']


class EnrollmentInline(admin.TabularInline):
    """نمایش و ویرایش رکوردهای مرتبط را به‌صورت درون‌خطی در پنل مدیریت فراهم می‌کند."""
    model = Enrollment
    extra = 0
    fields = ['student', 'status', 'payment_status', 'price_paid', 'progress_percentage', 'enrolled_at']
    readonly_fields = ['enrolled_at']
    autocomplete_fields = ['student']


class LessonProgressInline(admin.TabularInline):
    """نمایش و ویرایش رکوردهای مرتبط را به‌صورت درون‌خطی در پنل مدیریت فراهم می‌کند."""
    model = LessonProgress
    extra = 0
    readonly_fields = ['user', 'is_completed', 'completed_at']
    can_delete = False


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """نحوهٔ نمایش، جست‌وجو و فیلتر Course را در پنل مدیریت تنظیم می‌کند."""
    list_display = ['title', 'get_teachers', 'level', 'price', 'status', 'enroll_count']
    list_filter = ['level', 'status']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['teachers']
    inlines = [LessonInline, EnrollmentInline]
    readonly_fields = ['view_count', 'enroll_count', 'rating_avg']
    
    fieldsets = (
        ('اطلاعات اصلی', {'fields': ('title', 'slug', 'category', 'teachers', 'status', 'level')}),
        ('تصاویر', {'fields': ('thumbnail', 'cover_image')}),
        ('توضیحات', {'fields': ('short_description', 'description')}),
        ('قیمت', {'fields': ('price', 'discount_percent')}),
        ('آمار', {'fields': ('view_count', 'enroll_count', 'rating_avg')}),
    )
    
    def get_teachers(self, obj):
        """نام استادان دوره را برای ستون پنل مدیریت آماده می‌کند."""
        return ", ".join([t.get_full_name() or t.username for t in obj.teachers.all()][:3])
    get_teachers.short_description = "اساتید"


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    """نحوهٔ نمایش، جست‌وجو و فیلتر Lesson را در پنل مدیریت تنظیم می‌کند."""
    list_display = ['title', 'course', 'order', 'content_type', 'is_free_preview']
    list_filter = ['course', 'content_type', 'is_free_preview']
    search_fields = ['title', 'course__title']
    inlines = [LessonProgressInline]


@admin.register(CourseRating)
class CourseRatingAdmin(admin.ModelAdmin):
    """نحوهٔ نمایش، جست‌وجو و فیلتر CourseRating را در پنل مدیریت تنظیم می‌کند."""
    list_display = ['user', 'course', 'score', 'created_at']
    list_filter = ['score', 'course']
    search_fields = ['user__username', 'course__title']

    def save_model(self, request, obj, form, change):
        """امتیاز را ذخیره و خلاصهٔ امتیاز دوره را از سرویس بازسازی می‌کند."""
        super().save_model(request, obj, form, change)
        synchronize_course_rating_stats(obj.course)

    def delete_model(self, request, obj):
        """پس از حذف امتیاز، میانگین و تعداد دوره را اصلاح می‌کند."""
        course = obj.course
        super().delete_model(request, obj)
        synchronize_course_rating_stats(course)


@admin.register(LessonAttachment)
class LessonAttachmentAdmin(admin.ModelAdmin):
    """نحوهٔ نمایش، جست‌وجو و فیلتر LessonAttachment را در پنل مدیریت تنظیم می‌کند."""
    list_display = ['title', 'lesson', 'is_free', 'download_count']
    list_filter = ['is_free', 'lesson']