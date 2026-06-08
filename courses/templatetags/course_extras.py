from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """دسترسی به دیکشنری با کلید در تمپلیت"""
    return dictionary.get(key)