"""مدل ثبت‌نام دانش‌آموز در دوره، وضعیت پرداخت، پیشرفت و قوانین ظرفیت را تعریف می‌کند.

این فایل بخشی از پروژهٔ مدرسهٔ آنلاین است و مسئولیت‌های آن عمداً در همین دامنه نگه داشته شده‌اند.
"""

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from courses.models import Course


class Enrollment(models.Model):
    """
    مدل واسط ثبت‌نام دانشجو در دوره.
    این مدل به‌عنوان through برای Course.students عمل می‌کند،
    پس course.students / user.courses_enrolled همچنان کار می‌کنند،
    ولی علاوه بر آن تاریخ، وضعیت پرداخت و پیشرفت را هم نگه می‌دارد.
    """

    # وضعیت عضویت از وضعیت پرداخت جداست تا لغو یا تکمیل دوره مستقل مدیریت شود.
    STATUS_CHOICES = (
        ("active", "فعال"),
        ("completed", "تکمیل شده"),
        ("cancelled", "لغو شده"),
    )

    PAYMENT_CHOICES = (
        ("free", "رایگان"),
        ("pending", "در انتظار پرداخت"),
        ("paid", "پرداخت شده"),
        ("failed", "ناموفق"),
    )

    # هر رکورد، رابطهٔ واقعی میان یک دانش‌آموز و یک دوره را نمایش می‌دهد.
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="دانشجو",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="دوره",
    )

    # داده‌های عملیاتی ثبت‌نام برای گزارش مالی و پیگیری پیشرفت نگه‌داری می‌شوند.
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
        verbose_name="وضعیت",
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default="free",
        verbose_name="وضعیت پرداخت",
    )
    price_paid = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        verbose_name="مبلغ پرداختی (تومان)",
    )
    progress_percentage = models.PositiveSmallIntegerField(
        default=0, verbose_name="درصد پیشرفت"
    )

    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت‌نام")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="تاریخ تکمیل")

    class Meta:
        """تنظیمات متادیتا، ترتیب، نام نمایشی و محدودیت‌های این مدل یا فرم را تعریف می‌کند."""
        verbose_name = "ثبت‌نام"
        verbose_name_plural = "ثبت‌نام‌ها"
        unique_together = ["student", "course"]
        ordering = ["-enrolled_at"]
        indexes = [
            models.Index(fields=["student", "course"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        """نمایش خوانای این شیء را برای پنل مدیریت و گزارش‌ها برمی‌گرداند."""
        return f"{self.student} ← {self.course.title}"

    def clean(self):
        """✅ فیکس: کنترل ظرفیت در سطح مدل — تا از طریق ادمین جنگو هم
        نشود بیشتر از ظرفیت دوره ثبت‌نام کرد (view فقط فرانت را پوشش می‌دهد)."""
        if self.course_id and self.status != "cancelled":
            course = self.course
            if course.capacity:
                active_enrollments = course.enrollments.exclude(status="cancelled")
                if self.pk:
                    active_enrollments = active_enrollments.exclude(pk=self.pk)
                if active_enrollments.count() >= course.capacity:
                    raise ValidationError("ظرفیت این دوره تکمیل شده است.")

    @property
    def is_completed(self):
        """مشخص می‌کند این فرایند در وضعیت تکمیل‌شده قرار دارد یا نه."""
        return self.status == "completed"

    def mark_completed(self):
        """ثبت‌نام را تکمیل‌شده علامت بزن، به درد صدور گواهینامه می‌خورد."""
        self.status = "completed"
        self.progress_percentage = 100
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "progress_percentage", "completed_at"])
