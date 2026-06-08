from .models import Category

def categories_processor(request):
    # فقط دسته‌بندی‌های فعال را می‌گیریم
    return {
        'all_categories': Category.objects.filter(is_active=True).order_by('order')
    }
