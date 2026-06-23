from django.db.models import Count, Q
from .models import Category


def categories_processor(request):
    """
    دسته‌بندی‌ها را به همراه تعداد دوره (خود + زیردسته‌ها) برمی‌گرداند.
    """
    qs = Category.objects.filter(is_active=True).annotate(
        own_count=Count("courses", filter=Q(courses__status="published"), distinct=True),
    ).order_by("order")

    cats = list(qs)
    by_id = {c.id: c for c in cats}

    # مقداردهی اولیه
    for c in cats:
        c.total_courses_count = c.own_count

    # جمع تعداد دوره‌های هر زیردسته رو به پدرش اضافه کن
    for c in cats:
        if c.parent_id and c.parent_id in by_id:
            by_id[c.parent_id].total_courses_count += c.own_count

    return {"all_categories": cats}
