from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# EduPlatform/urls.py



urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('courses/', include('courses.urls')),  # این خط باید باشد
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
