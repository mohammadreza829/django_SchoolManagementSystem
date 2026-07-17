"""فیلترهای کمکی قالب برای خواندن امن مقدار از دیکشنری‌ها را تعریف می‌کند.

این فایل بخشی از پروژهٔ مدرسهٔ آنلاین است و مسئولیت‌های آن عمداً در همین دامنه نگه داشته شده‌اند.
"""

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """دسترسی به دیکشنری با کلید در تمپلیت"""
    return dictionary.get(key)