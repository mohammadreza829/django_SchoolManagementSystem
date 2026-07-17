"""مدل پیام چت دوره، فرستنده، متن، اعلان استاد و زمان ارسال را تعریف می‌کند.

 
"""

from django.db import models
from django.conf import settings
from courses.models import Course


class CourseMessage(models.Model):
    """یک پیام در چت‌روم یک دوره."""

    # پیام همیشه به یک دوره و یک فرستندهٔ مشخص تعلق دارد.
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="دوره",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_messages",
        verbose_name="فرستنده",
    )
    # متن خام ذخیره می‌شود و escaping آن بر عهدهٔ قالب یا پاسخ JSON است.
    text = models.TextField(verbose_name="متن پیام")
    is_announcement = models.BooleanField(
        default=False, verbose_name="اعلان استاد"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ارسال")

    class Meta:
        """تنظیمات متادیتا، ترتیب، نام نمایشی و محدودیت‌های این مدل یا فرم را تعریف می‌کند."""
        verbose_name = "پیام دوره"
        verbose_name_plural = "پیام‌های دوره"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["course", "created_at"])]

    def __str__(self):
        """نمایش خوانای این شیء را برای پنل مدیریت و گزارش‌ها برمی‌گرداند."""
        return f"{self.sender} → {self.course.title}: {self.text[:30]}"
