"""دسته‌بندی‌های فعال و شمار دوره‌های منتشرشده را برای استفادهٔ سراسری در قالب‌ها آماده می‌کند.

 
"""

from django.db.models import Count, Q
from .models import Category


def categories_processor(request):
    """
    دسته‌بندی‌ها را به همراه تعداد دوره (خود + زیردسته‌ها) برمی‌گرداند.
    """
    categories_queryset = Category.objects.filter(is_active=True).annotate(
        own_count=Count(
            "courses",
            filter=Q(courses__status="published"),
            distinct=True,
        ),
    ).order_by("order")

    categories = list(categories_queryset)
    categories_by_id = {category.id: category for category in categories}

    # ابتدا شمار مستقیم هر دسته ثبت می‌شود؛ سپس شمار زیردسته به والد افزوده می‌شود.
    for category in categories:
        category.total_courses_count = category.own_count

    for category in categories:
        parent = categories_by_id.get(category.parent_id)
        if parent is not None:
            parent.total_courses_count += category.own_count

    return {"all_categories": categories}
