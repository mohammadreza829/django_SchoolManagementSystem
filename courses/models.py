# courses/models.py

from django.db import models
from django.urls import reverse
from django.conf import settings
from accounts.models import User  # برای ارتباط با مدل User


class Category(models.Model):
    """دسته‌بندی دوره‌ها"""

    name = models.CharField(max_length=100, unique=True, verbose_name="نام دسته")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="slug")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="subcategories",
        verbose_name="دسته والد",
    )
    icon = models.CharField(max_length=50, blank=True, verbose_name="آیکون")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ["order", "name"]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Course(models.Model):
    """
    مدل دوره‌های آموزشی
    """

    # سطح دوره
    LEVEL_CHOICES = (
        ("beginner", "مقدماتی"),
        ("intermediate", "متوسط"),
        ("advanced", "پیشرفته"),
    )

    # وضعیت دوره
    STATUS_CHOICES = (
        ("draft", "پیش‌نویس"),
        ("published", "منتشر شده"),
        ("coming_soon", "به زودی"),
        ("archived", "بایگانی شده"),
    )

    # ========== فیلدهای اصلی ==========
    title = models.CharField(
        max_length=200,
        verbose_name="عنوان دوره",
        help_text="نام دوره (مثلاً: آموزش جنگو پیشرفته)",
    )

    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name="slug",
        help_text="آدرس یکتا برای سئو (فیلد خودکار می‌شود)",
    )

    # 🔥 مهم: رابطه چند به چند با استادها
    teachers = models.ManyToManyField(
        User,
        related_name="courses_teaching",  # استاد: user.courses_teaching.all()
        limit_choices_to={"role": "teacher"},  # فقط افرادی که نقش استاد دارند
        verbose_name="اساتید دوره",
        help_text="می‌توانید چند استاد برای این دوره انتخاب کنید",
    )

    # رابطه یک به چند با دانشجوها (کسانی که ثبت‌نام کردند)
    students = models.ManyToManyField(
        User,
        related_name="courses_enrolled",
        blank=True,
        verbose_name="دانشجویان ثبت‌نام شده",
        help_text="دانش‌آموزانی که در این دوره ثبت‌نام کرده‌اند",
    )

    description = models.TextField(
        verbose_name="توضیحات کامل", help_text="توضیحات کامل دوره"
    )

    short_description = models.CharField(
        max_length=300,
        verbose_name="توضیحات کوتاه",
        help_text="برای نمایش در کنار عنوان دوره",
    )

    # ========== فیلدهای تصاویر ==========
    thumbnail = models.ImageField(
        upload_to="courses/thumbnails/%Y/%m/",
        verbose_name="تصویر بندانگشتی",
        help_text="تصویر کوچک برای کارت‌های دوره",
        blank=True,
        null=True,
    )

    cover_image = models.ImageField(
        upload_to="courses/covers/%Y/%m/",
        verbose_name="تصویر شاخص",
        help_text="تصویر بزرگ برای صفحه اصلی دوره",
        blank=True,
        null=True,
    )

    # ========== فیلدهای سطح و وضعیت ==========
    level = models.CharField(
        max_length=15,
        choices=LEVEL_CHOICES,
        default="beginner",
        verbose_name="سطح دوره",
    )

    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default="draft", verbose_name="وضعیت"
    )

    # ========== فیلدهای قیمت و تخفیف ==========
    price = models.DecimalField(
        max_digits=10,  # حداکثر 10 رقم
        decimal_places=0,  # بدون اعشار (تومان)
        default=0,
        verbose_name="قیمت (تومان)",
        help_text="قیمت دوره به تومان",
    )

    discount_percent = models.PositiveSmallIntegerField(
        default=0, verbose_name="درصد تخفیف", help_text="عدد بین 0 تا 100"
    )

    # ========== فیلدهای زمان‌بندی ==========
    duration_hours = models.PositiveSmallIntegerField(
        default=0, verbose_name="مدت دوره (ساعت)"
    )

    total_lessons = models.PositiveSmallIntegerField(
        default=0, verbose_name="تعداد جلسات", help_text="تعداد کل ویدیوهای آموزشی"
    )

    # ========== فیلدهای تاریخ ==========
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ ویرایش")
    published_at = models.DateTimeField(
        blank=True, null=True, verbose_name="تاریخ انتشار"
    )

    # ========== فیلدهای آمار ==========
    view_count = models.PositiveIntegerField(default=0, verbose_name="تعداد بازدید")
    enroll_count = models.PositiveIntegerField(default=0, verbose_name="تعداد ثبت‌نام")
    rating_avg = models.DecimalField(
        max_digits=3, decimal_places=2, default=0, verbose_name="میانگین امتیاز"
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
        verbose_name="دسته‌بندی",
    )
    rating_count = models.PositiveIntegerField(default=0, verbose_name="تعداد امتیازها")
    rating_avg = models.DecimalField(
        max_digits=3, decimal_places=2, default=0, verbose_name="میانگین امتیاز"
    )

    # ========== متادیتا ==========
    class Meta:
        verbose_name = "دوره"
        verbose_name_plural = "دوره‌ها"
        ordering = ["-created_at"]  # جدیدترین اول
        indexes = [
            models.Index(fields=["title"]),  # برای جستجوی سریع
            models.Index(fields=["slug"]),  # برای URL
            models.Index(fields=["status", "created_at"]),  # فیلتر ترکیبی
        ]

    def __str__(self):
        return f"{self.title} - {self.get_teachers_names()}"

    def get_teachers_names(self):
        """بازگرداندن نام همه استادهای این دوره با کاما"""
        return ", ".join(
            [
                teacher.get_full_name() or teacher.username
                for teacher in self.teachers.all()
            ]
        )

    def get_teachers_list(self):
        """بازگرداندن لیست استادها برای استفاده در template"""
        return self.teachers.filter(role="teacher")

    @property
    def final_price(self):
        """محاسبه قیمت بعد از تخفیف"""
        if self.discount_percent > 0:
            return int(self.price * (100 - self.discount_percent) / 100)
        return int(self.price)

    @property
    def is_free(self):
        """آیا دوره رایگان است؟"""
        return self.final_price == 0

    def get_absolute_url(self):
        return reverse("courses:course_detail", kwargs={"slug": self.slug})


# courses/models.py - بعد از مدل Course اضافه کن


class Lesson(models.Model):
    """جلسات آموزشی هر دوره"""

    CONTENT_TYPE_CHOICES = (
        ("video", "ویدیو آموزشی"),
        ("article", "متن آموزشی"),
        ("file", "فایل آموزشی"),
    )

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="lessons", verbose_name="دوره"
    )
    title = models.CharField(max_length=200, verbose_name="عنوان جلسه")
    slug = models.SlugField(max_length=200, blank=True, verbose_name="slug")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")

    # محتوا
    content_type = models.CharField(
        max_length=20, choices=CONTENT_TYPE_CHOICES, default="video"
    )
    video_url = models.URLField(blank=True, verbose_name="لینک ویدیو")
    video_file = models.FileField(
        upload_to="courses/videos/%Y/%m/", blank=True, null=True
    )
    article_content = models.TextField(blank=True, verbose_name="متن آموزشی")

    # دسترسی
    is_free_preview = models.BooleanField(
        default=False, verbose_name="پیش‌نمایش رایگان"
    )
    duration_minutes = models.PositiveSmallIntegerField(
        default=0, verbose_name="مدت (دقیقه)"
    )

    # آمار
    view_count = models.PositiveIntegerField(default=0, verbose_name="تعداد بازدید")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "جلسه"
        verbose_name_plural = "جلسات"
        ordering = ["order"]
        unique_together = ["course", "order"]

    def __str__(self):
        return f"{self.course.title} - جلسه {self.order}: {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify

            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_video(self):
        """دریافت آدرس ویدیو"""
        return self.video_file.url if self.video_file else self.video_url


# courses/models.py - بعد از Lesson اضافه کن


class LessonProgress(models.Model):
    """پیشرفت دانش‌آموز در هر جلسه"""

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="progresses"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="lesson_progresses"
    )
    is_completed = models.BooleanField(default=False, verbose_name="تکمیل شده")
    completed_at = models.DateTimeField(blank=True, null=True)
    last_watched = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "پیشرفت جلسه"
        verbose_name_plural = "پیشرفت جلسات"
        unique_together = ["lesson", "user"]

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title}: {'✓' if self.is_completed else '○'}"


# courses/models.py - بعد از LessonProgress اضافه کن


# courses/models.py


class CourseRating(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="course_ratings"
    )
    score = models.PositiveSmallIntegerField(verbose_name="امتیاز (1-5)")
    comment = models.TextField(blank=True, verbose_name="نظر")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["course", "user"]
        verbose_name = "امتیاز "
        verbose_name_plural = "امتیاز ها"
    def __str__(self):
        return f"{self.user.username} → {self.course.title}: {self.score}⭐"
    verbose_name = "امتیاز "
    verbose_name_plural = "امتیاز ها"


# courses/models.py - آخر فایل اضافه کن


class LessonAttachment(models.Model):
    """فایل‌های ضمیمه جلسه (PDF، PPT، و ...)"""

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="attachments"
    )
    title = models.CharField(max_length=200, verbose_name="عنوان فایل")
    file = models.FileField(upload_to="courses/attachments/%Y/%m/", verbose_name="فایل")
    is_free = models.BooleanField(default=False, verbose_name="رایگان")
    download_count = models.PositiveIntegerField(default=0, verbose_name="تعداد دانلود")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ضمیمه"
        verbose_name_plural = "ضمیمه‌ها"

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"
