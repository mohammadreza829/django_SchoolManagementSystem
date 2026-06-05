from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    # مسیرهای دیگر مثل courses را هم اگر داری اضافه کن
]

# اضافه کردن این بخش برای سرو دهی فایل‌های رسانه در حالت DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
