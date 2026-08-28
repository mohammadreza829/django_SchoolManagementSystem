"""
سرویس اتصال به API هوش مصنوعی (سازگار با OpenAI Chat Completions).

پیش‌فرض پروژه: درگاه TabiAI روی tabitoken.com
با هر سرویس سازگار با OpenAI هم کار می‌کند (DeepSeek، OpenAI، OpenRouter و...).

تنظیمات (در EduPlatform/ai_settings.py از متغیرهای محیطی/.env خوانده می‌شوند):
  AI_API_BASE_URL   مثلا https://tabitoken.com/v1
  AI_API_KEY        کلید API (اجباری — فقط در .env)
  AI_MODEL          مثلا gpt-4o-mini
  AI_TIMEOUT_SECONDS

از کتابخانه‌ی استاندارد (urllib) استفاده شده تا وابستگی جدیدی لازم نباشد.
"""

import json
import urllib.error
import urllib.request

from django.conf import settings

# اگر مدل تشخیص دهد سوال غیرآموزشی است، فقط این عبارت را برمی‌گرداند
REJECTION_MARKER = "[OFF_TOPIC]"

SYSTEM_PROMPT = (
    "تو «دستیار آموزشی» یک پلتفرم مدرسه و کلاس آنلاین هستی. "
    "وظیفه‌ی تو فقط پاسخ به سوال‌های درسی و آموزشی است: ریاضی، فیزیک، شیمی، "
    "زیست، برنامه‌نویسی و کامپیوتر، زبان، مفاهیم علمی و سوال‌های مربوط به محتوای دوره‌ها.\n"
    "قوانین:\n"
    "1) فقط به سوال‌های آموزشی پاسخ بده. اگر سوال نامرتبط بود (سیاسی، شخصی، "
    "پزشکی، حقوقی، سرگرمی و...) فقط و فقط عبارت " + REJECTION_MARKER + " را برگردان و هیچ چیز دیگری ننویس.\n"
    "2) پاسخ را به فارسی روان و در صورت نیاز مرحله‌به‌مرحله بده.\n"
    "3) پاسخ کوتاه و مفید باشد (حداکثر حدود ۳۰۰ کلمه).\n"
    "4) اگر سوال مبهم است، مؤدبانه درخواست توضیح بیشتر کن.\n"
    "5) جواب مستقیم تکلیف یا امتحان را لو نده؛ به‌جای آن روش حل را آموزش بده."
)


class AiServiceError(Exception):
    """خطای سرویس هوش مصنوعی (کلید، شبکه، پاسخ نامعتبر و...)"""


def ask_ai(question, course_title=None):
    """
    سوال را به مدل می‌فرستد.

    خروجی: (answer_text, is_rejected)
    در صورت مشکل، AiServiceError بالا می‌آید.
    """
    api_key = getattr(settings, "AI_API_KEY", "")
    if not api_key:
        raise AiServiceError("کلید API تنظیم نشده است (AI_API_KEY در فایل .env).")

    base_url = getattr(settings, "AI_API_BASE_URL", "https://tabitoken.com/v1").rstrip("/")
    model = getattr(settings, "AI_MODEL", "gpt-4o-mini")
    timeout = getattr(settings, "AI_TIMEOUT_SECONDS", 60)

    user_content = question.strip()
    if course_title:
        user_content = f"(این سوال مربوط به دوره‌ی «{course_title}» است)\n{user_content}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": 800,
        "temperature": 0.3,
    }

    req = urllib.request.Request(
        base_url + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8")[:300]
        except Exception:
            pass
        raise AiServiceError(f"خطای سرویس (کد {exc.code}). {detail}") from exc
    except urllib.error.URLError as exc:
        raise AiServiceError(f"عدم دسترسی به سرویس: {exc.reason}") from exc
    except TimeoutError as exc:
        raise AiServiceError("پاسخ‌گویی سرویس بیش از حد طول کشید.") from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise AiServiceError("پاسخ نامعتبر از سرویس دریافت شد.") from exc

    try:
        answer = body["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise AiServiceError("ساختار پاسخ سرویس نامعتبر بود.") from exc

    is_rejected = REJECTION_MARKER in answer
    return answer, is_rejected
