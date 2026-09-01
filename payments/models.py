"""مدل تراکنش پرداخت درگاه (زرین‌پال) را تعریف می‌کند.

هر تراکنش به یک ثبت‌نام مشخص گره می‌خورد تا مسیر پرداخت قابل رهگیری و
idempotent بماند؛ منطق باز کردن دسترسی همچنان در courses.services است.
"""

from django.conf import settings
from django.db import models

from courses.models import Course
from Enrollment.models import Enrollment


class Payment(models.Model):
    """یک تلاش پرداخت برای ثبت‌نام در یک دورهٔ پولی."""

    STATUS_INITIATED = "initiated"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_INITIATED, "شروع‌شده"),
        (STATUS_PAID, "پرداخت‌شده"),
        (STATUS_FAILED, "ناموفق"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="کاربر",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="دوره",
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="ثبت‌نام",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name="مبلغ (تومان)",
    )
    authority = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        verbose_name="کد Authority زرین‌پال",
    )
    ref_id = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="کد رهگیری (RefID)",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_INITIATED,
        verbose_name="وضعیت",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین به‌روزرسانی")

    class Meta:
        verbose_name = "پرداخت"
        verbose_name_plural = "پرداخت‌ها"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="payment_status_created_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["authority"],
                condition=models.Q(authority__gt=""),
                name="payment_authority_unique_when_set",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name="payment_amount_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.user} → {self.course.title}: {self.get_status_display()}"
