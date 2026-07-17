"""مسیرهای سطح پروژه را تعریف می‌کند و URLهای اپ‌های حساب، دوره، آزمون، پنل، چت و پرسش‌وپاسخ را به یکدیگر متصل می‌کند.

این فایل بخشی از پروژهٔ مدرسهٔ آنلاین است و مسئولیت‌های آن عمداً در همین دامنه نگه داشته شده‌اند.
"""

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
    path('panel/', include('panel.urls')),  # پنل مدیریت
    path('chat/', include('chat.urls')),    # چت دوره‌ها
    path('qa/', include('qa.urls'))
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
