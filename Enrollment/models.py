from django.db import models
from django.conf import settings
from django.utils import timezone
from courses.models import Course


class Enrollment(models.Model):
    """
    مدل واسط ثبت‌نام دانشجو در دوره.
    این مدل به‌عنوان through برای Course.students عمل می‌کند،
    پس course.students / user.courses_enrolled همچنان کار می‌کنند،
    ولی علاوه بر آن تاریخ، وضعیت پرداخت و پیشرفت را هم نگه می‌دارد.
    """

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
        verbose_name = "ثبت‌نام"
        verbose_name_plural = "ثبت‌نام‌ها"
        unique_together = ["student", "course"]
        ordering = ["-enrolled_at"]
        indexes = [
            models.Index(fields=["student", "course"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.student} ← {self.course.title}"

    @property
    def is_completed(self):
        return self.status == "completed"

    def mark_completed(self):
        """ثبت‌نام را تکمیل‌شده علامت بزن، به درد صدور گواهینامه می‌خورد."""
        self.status = "completed"
        self.progress_percentage = 100
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "progress_percentage", "completed_at"])
