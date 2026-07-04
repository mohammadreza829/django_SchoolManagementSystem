"""
تنظیمات دستیار هوش مصنوعی (بخش پرسش‌ها) — پیکربندی‌شده برای DeepSeek.

طرز استفاده: این فایل را کنار settings.py بگذار و آخر settings.py فقط یک خط اضافه کن:

    from .ai_settings import *

مقادیر از متغیرهای محیطی یا فایل .env کنار manage.py خوانده می‌شوند.
کلید API را داخل کد نگذار؛ فقط در .env (که در .gitignore است) نگه‌داری کن.
"""

import os
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv():
    """اگر فایل .env کنار manage.py باشد، مقادیرش را به متغیرهای محیطی اضافه می‌کند.
    (مقادیری که از قبل در محیط تنظیم شده باشند دست‌نخورده می‌مانند.)"""
    env_file = _BASE_DIR / ".env"
    if not env_file.exists():
        return
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

# ============ تنظیمات دستیار هوش مصنوعی ============
AI_API_BASE_URL = os.environ.get("AI_API_BASE_URL", "https://api.deepseek.com/v1")
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_MODEL = os.environ.get("AI_MODEL", "deepseek-chat")
AI_TIMEOUT_SECONDS = int(os.environ.get("AI_TIMEOUT_SECONDS", "60"))
AI_DAILY_LIMIT = int(os.environ.get("AI_DAILY_LIMIT", "10"))
