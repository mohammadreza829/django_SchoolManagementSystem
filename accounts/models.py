from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.urls import reverse
from django.conf import settings
from datetime import date

# ==================== مدیر کاربران ====================
class UserManager(BaseUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError("نام کاربری باید تنظیم شود")
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("سوپریوزر باید is_staff=True داشته باشد.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("سوپریوزر باید is_superuser=True داشته باشد.")

        return self.create_user(username, email, password, **extra_fields)


# ==================== مدل کاربر اختصاصی ====================
class User(AbstractUser):
    ROLE_CHOICES = (
        ("admin", "مدیر"),
        ("teacher", "استاد"),
        ("student", "دانش‌آموز"),
        ("parent", "والدین"),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="student", verbose_name="نقش")
    phone = models.CharField(max_length=13, unique=True, blank=True, null=True, verbose_name="شماره تلفن")
    national_code = models.CharField(max_length=10, unique=True, verbose_name="کد ملی")
    email = models.EmailField(unique=True)
    objects = UserManager()

    REQUIRED_FIELDS = ["national_code", 'email'] 

    class Meta:
        ordering = ["date_joined"]
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_teacher(self):
        return self.role == "teacher"

    @property
    def is_student(self):
        return self.role == "student"


# ==================== مدل پروفایل عمومی (برای همه نقش‌ها) ====================
class Profile(models.Model):
    GENDER_CHOICES = (
        ('male', 'مرد'),
        ('female', 'زن'),
        ('other', 'سایر'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='کاربر'
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='بیوگرافی',
        help_text='توضیحات کوتاه درباره خودتان'
    )
    avatar = models.ImageField(
        upload_to='accounts/avatars/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name='تصویر پروفایل',
        help_text='تصویر نمایه شما'
    )
    cover_image = models.ImageField(
        upload_to='accounts/covers/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name='تصویر پوشش',
        help_text='تصویر پوشش پروفایل'
    )
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
        verbose_name='جنسیت'
    )
    birth_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='تاریخ تولد',
        help_text='تاریخ تولد شما'
    )
    website = models.URLField(blank=True, null=True, verbose_name='وب‌سایت')
    location = models.CharField(max_length=100, blank=True, null=True, verbose_name='محل سکونت')

    # شبکه‌های اجتماعی
    twitter = models.CharField(max_length=100, blank=True, null=True, verbose_name='توییتر')
    instagram = models.CharField(max_length=100, blank=True, null=True, verbose_name='اینستاگرام')
    linkedin = models.CharField(max_length=100, blank=True, null=True, verbose_name='لینکدین')
    github = models.CharField(max_length=100, blank=True, null=True, verbose_name='گیت‌هاب')

    # تاریخ‌ها و آمارها
    last_seen = models.DateTimeField(auto_now=True, verbose_name='آخرین بازدید')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ ویرایش')
    
    # این آمارها را می‌توان برای بخش وبلاگ یا دوره‌ها استفاده کرد
    posts_count = models.PositiveIntegerField(default=0, verbose_name='تعداد مقالات')
    comments_count = models.PositiveIntegerField(default=0, verbose_name='تعداد نظرات')

    class Meta:
        verbose_name = 'پروفایل عمومی'
        verbose_name_plural = 'پروفایل‌های عمومی'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['gender']),
            models.Index(fields=['location']),
        ]

    def __str__(self):
        return f'پروفایل عمومی {self.user.username}'

    def get_absolute_url(self):
        return reverse('accounts:profile_detail', kwargs={'username': self.user.username})

    def get_age(self):
        if self.birth_date:
            today = date.today()
            return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None

    def is_birthday(self):
        if self.birth_date:
            today = date.today()
            return today.month == self.birth_date.month and today.day == self.birth_date.day
        return False

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return f'{settings.STATIC_URL}images/default-avatar.png'

    def get_cover_url(self):
        if self.cover_image:
            return self.cover_image.url
        return f'{settings.STATIC_URL}images/default-cover.jpg'


# ==================== مدل پروفایل اختصاصی استاد ====================
class TeacherProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="teacher_profile", verbose_name="کاربر"
    )
    specialty = models.CharField(max_length=100, verbose_name="تخصص")
    degree = models.CharField(max_length=50, blank=True, null=True, verbose_name="مدرک تحصیلی")

    class Meta:
        verbose_name = "پروفایل استاد"
        verbose_name_plural = "پروفایل‌های اساتید"

    def __str__(self):
        return f"استاد: {self.user.get_full_name() or self.user.username}"


# ==================== مدل پروفایل اختصاصی دانش‌آموز ====================
class StudentProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="student_profile", verbose_name="کاربر"
    )
    student_id = models.CharField(max_length=20, unique=True, verbose_name="شماره دانش‌آموزی")
    entry_year = models.IntegerField(default=1403, verbose_name="سال ورود")

    class Meta:
        verbose_name = "پروفایل دانش‌آموز"
        verbose_name_plural = "پروفایل‌های دانش‌آموزان"

    def __str__(self):
        return f"دانش‌آموز: {self.user.get_full_name() or self.user.username}"


# ==================== مدل اعلان‌ها (Notifications) ====================
class Notification(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications', verbose_name="کاربر"
    )
    message = models.CharField(max_length=255, verbose_name="پیام")
    link = models.CharField(max_length=500, blank=True, default="", verbose_name="لینک مقصد")
    title = models.CharField(max_length=120, blank=True, default="", verbose_name="عنوان")
    is_read = models.BooleanField(default=False, verbose_name="خوانده شده؟")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        verbose_name = "اعلان"
        verbose_name_plural = "اعلان‌ها"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.message}"
