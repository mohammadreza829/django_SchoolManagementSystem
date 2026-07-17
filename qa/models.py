"""مدل تاریخچهٔ سؤال، پاسخ، وضعیت، مدل استفاده‌شده و زمان پاسخ سرویس هوش مصنوعی را تعریف می‌کند.

 
"""

from django.conf import settings
from django.db import models

from courses.models import Course


class AiQuestion(models.Model):
    """یک پرسش کاربر از دستیار هوش مصنوعی + پاسخ آن."""

    # نگه‌داری وضعیت شکست و ردشدن، پایش کیفیت و هزینهٔ سرویس را ممکن می‌کند.
    STATUS_CHOICES = [
        ("answered", "پاسخ داده شد"),
        ("rejected", "خارج از محدوده آموزشی"),
        ("failed", "خطا در دریافت پاسخ"),
    ]

    # مالک پرسش و دورهٔ اختیاری برای تاریخچه و کنترل دسترسی ثبت می‌شوند.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_questions",
        verbose_name="کاربر",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_questions",
        verbose_name="دوره (اختیاری)",
    )
    # پاسخ و متادیتای سرویس برای عیب‌یابی و نمایش تاریخچه نگه‌داری می‌شوند.
    question = models.TextField(verbose_name="پرسش")
    answer = models.TextField(blank=True, verbose_name="پاسخ")
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="answered",
        verbose_name="وضعیت",
    )
    model_used = models.CharField(max_length=100, blank=True, verbose_name="مدل")
    response_ms = models.PositiveIntegerField(default=0, verbose_name="زمان پاسخ (ms)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان")

    class Meta:
        """تنظیمات متادیتا، ترتیب، نام نمایشی و محدودیت‌های این مدل یا فرم را تعریف می‌کند."""
        verbose_name = "پرسش هوشمند"
        verbose_name_plural = "پرسش‌های هوشمند"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "created_at"])]

    def __str__(self):
        """نمایش خوانای این شیء را برای پنل مدیریت و گزارش‌ها برمی‌گرداند."""
        return f"{self.user}: {self.question[:40]}"
