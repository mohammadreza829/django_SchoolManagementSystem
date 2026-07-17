"""فیلترهای کمکی قالب برای خواندن امن مقدار از دیکشنری‌ها را تعریف می‌کند.

 
"""

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """دسترسی به دیکشنری با کلید در تمپلیت"""
    return dictionary.get(key)