from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from .models import User, Profile, TeacherProfile, StudentProfile, Notification


# ==================== ۱. مدیریت کاربر ====================
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'full_name', 'role', 'email', 'phone', 'national_code', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'national_code')
    list_editable = ('role', 'is_active')
    ordering = ('-date_joined',)
    
    fieldsets = (
        ('اطلاعات ورود', {
            'fields': ('username', 'password')
        }),
        ('اطلاعات شخصی', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'national_code')
        }),
        ('نقش و دسترسی‌ها', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('تاریخ‌ها', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'email', 'phone', 'national_code', 'role', 'password1', 'password2'),
        }),
    )
    
    def full_name(self, obj):
        return obj.get_full_name() or obj.username
    full_name.short_description = 'نام کامل'
    full_name.admin_order_field = 'first_name'


# ==================== ۲. مدیریت پروفایل عمومی ====================
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'get_full_name', 'gender', 'location',
        'posts_count', 'comments_count', 'last_seen'
    )
    list_filter = ('gender', 'location', 'last_seen')
    search_fields = (
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
        'bio', 'location', 'twitter', 'instagram', 'linkedin', 'github'
    )
    readonly_fields = ('last_seen', 'updated_at', 'posts_count', 'comments_count')
    ordering = ('-last_seen',)

    fieldsets = (
        ('اطلاعات کاربر', {
            'fields': ('user', 'gender', 'birth_date', 'bio')
        }),
        ('تصاویر', {
            'fields': ('avatar', 'cover_image')
        }),
        ('شبکه‌های اجتماعی', {
            'fields': ('website', 'location', 'twitter', 'instagram', 'linkedin', 'github')
        }),
        ('آمار و تاریخ‌ها', {
            'fields': ('posts_count', 'comments_count', 'last_seen', 'updated_at')
        }),
    )
    
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = 'نام کامل'


# ==================== ۳. مدیریت پروفایل استاد ====================
@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'specialty', 'degree')
    list_filter = ('specialty', 'degree')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'specialty')
    
    fieldsets = (
        ('اطلاعات استاد', {
            'fields': ('user', 'specialty', 'degree')
        }),
    )
    
    def full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    full_name.short_description = 'نام کامل'


# ==================== ۴. مدیریت پروفایل دانش‌آموز ====================
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'student_id', 'entry_year')
    list_filter = ('entry_year',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'student_id')
    readonly_fields = ('student_id',)
    
    fieldsets = (
        ('اطلاعات دانش‌آموز', {
            'fields': ('user', 'student_id', 'entry_year')
        }),
    )
    
    def full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    full_name.short_description = 'نام کامل'


# ==================== ۵. مدیریت اعلان‌ها ====================
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'message')
    list_editable = ('is_read',)
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {
            'fields': ('user', 'message', 'is_read', 'created_at')
        }),
    )
    
    def full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    full_name.short_description = 'نام کاربر'
    
    
    
    