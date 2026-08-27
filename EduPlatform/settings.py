"""تنظیمات پروژهٔ EduPlatform.

همهٔ مقادیر حساس (کلید جنگو، رمز دیتابیس، کلید هوش مصنوعی) فقط از متغیرهای
محیطی یا فایل `.env` کنار `manage.py` خوانده می‌شوند؛ نمونهٔ آن در
`.env.example` است. هیچ رمزی نباید داخل این فایل نوشته شود.

مستندات: https://docs.djangoproject.com/en/6.0/ref/settings/
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

# ایمپورت تنظیمات هوش مصنوعی در همین ابتدا انجام می‌شود چون همان ماژول فایل
# `.env` را در os.environ بار می‌کند و بقیهٔ تنظیمات به آن متغیرها نیاز دارند.
from .ai_settings import *  # noqa: E402,F401,F403


# ==================== کمکی‌های خواندن محیط ====================
def env(name, default=""):
    """مقدار متغیر محیطی را به‌صورت رشتهٔ trim‌شده برمی‌گرداند."""
    return os.environ.get(name, default).strip()


def env_bool(name, default=False):
    """مقدار متغیر محیطی را به بولین تبدیل می‌کند."""
    return env(name, "true" if default else "false").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def env_list(name, default=""):
    """مقدار کاما-جدا را به لیستی از رشته‌های غیرخالی تبدیل می‌کند."""
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


# ==================== امنیت و محیط اجرا ====================
DEBUG = env_bool("DJANGO_DEBUG", False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY تنظیم نشده است. برای اجرای بدون DEBUG الزامی است."
        )
    # فقط برای توسعهٔ محلی؛ با هر ری‌استارت عوض می‌شود و سشن‌ها باطل می‌شوند.
    SECRET_KEY = get_random_secret_key()

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# هاردنینگ فقط در محیط واقعی فعال می‌شود تا توسعهٔ محلی روی http مختل نشود.
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# ==================== اپلیکیشن‌ها ====================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "courses",
    "Enrollment",
    "quiz",
    "panel",
    "chat",
    "qa",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise باید بلافاصله بعد از SecurityMiddleware باشد تا فایل‌های
    # استاتیک را در محیط واقعی (بدون nginx) سرو کند.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "EduPlatform.urls"
WSGI_APPLICATION = "EduPlatform.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "courses.context_processors.categories_processor",
                "accounts.context_processors.notifications_processor",
            ],
        },
    },
]


# ==================== دیتابیس ====================
# پیش‌فرض پستگرس است؛ با DJANGO_DB_ENGINE=sqlite می‌توان تست‌ها را بدون
# نصب پستگرس اجرا کرد.
if env("DJANGO_DB_ENGINE", "postgresql").lower() == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DJANGO_DB_NAME", "eduplatform"),
            "USER": env("DJANGO_DB_USER", "eduplatform_admin"),
            "PASSWORD": env("DJANGO_DB_PASSWORD"),
            "HOST": env("DJANGO_DB_HOST", "localhost"),
            "PORT": env("DJANGO_DB_PORT", "5432"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"


# ==================== بومی‌سازی ====================
LANGUAGE_CODE = "fa"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True


# ==================== فایل‌های ایستا و رسانه ====================
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise: فشرده‌سازی و سرو فایل‌های استاتیک در محیط واقعی بدون nginx.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
