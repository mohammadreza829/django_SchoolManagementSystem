from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import home

# EduPlatform/urls.py



urlpatterns = [
    path('', home, name='home'),  # صفحه اصلی (لندینگ)
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('courses/', include('courses.urls')),  # این خط باید باشد
    path('quiz/', include('quiz.urls')),  # این خط باید باشد
    path('panel/', include('panel.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
