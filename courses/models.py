# courses/models.py

from django.db import models
from django.urls import reverse
from django.conf import settings
from accounts.models import User  # برای ارتباط با مدل User


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
    )

    cover_image = models.ImageField(
        upload_to="courses/covers/%Y/%m/",
        verbose_name="تصویر شاخص",
        help_text="تصویر بزرگ برای صفحه اصلی دوره",
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
