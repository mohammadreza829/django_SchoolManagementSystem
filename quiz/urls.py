"""مبدل slug فارسی و مسیرهای فهرست، جزئیات، شرکت، نتیجه و پیشرفت آزمون را تعریف می‌کند.

این فایل بخشی از پروژهٔ مدرسهٔ آنلاین است و مسئولیت‌های آن عمداً در همین دامنه نگه داشته شده‌اند.
"""

# quiz/urls.py
from django.urls import path, register_converter
from . import views


class UnicodeSlugConverter:
    """مثل کانورتر slug پیش‌فرض جنگو، اما حروف یونیکد (فارسی) را هم می‌پذیرد.
    الگوی word-character در پایتون ۳ به‌صورت پیش‌فرض یونیکد‌آگاه است و حروف فارسی را شامل می‌شود."""
    regex = r"[-\w]+"

    def to_python(self, value):
        """مقدار slug دریافت‌شده از URL را بدون تغییر به view تحویل می‌دهد."""
        return value

    def to_url(self, value):
        """مقدار slug را برای ساخت URL به رشتهٔ قابل استفاده تبدیل می‌کند."""
        return value


register_converter(UnicodeSlugConverter, "uslug")

app_name = "quiz"

urlpatterns = [
    # لیست همه‌ی آزمون‌ها
    path("", views.quiz_list, name="quiz_list"),
    # مسیرهای ثابت اول بیایند تا با اسلاگ تداخل نکنند
    path("my-progress/", views.my_progress, name="my_progress"),
    path("attempt/<int:attempt_id>/result/", views.quiz_result, name="quiz_result"),
    # صفحه‌ی دادن آزمون (قبل از quiz_detail تا take/ درست مچ بشود)
    path("<uslug:slug>/take/", views.take_quiz, name="take_quiz"),
    # صفحه‌ی معرفی آزمون
    path("<uslug:slug>/", views.quiz_detail, name="quiz_detail"),
]
