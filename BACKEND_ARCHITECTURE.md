# معماری بک‌اند پس از بازآرایی

## لایه‌ها

- `models.py`: ساختار داده، رابطه‌ها و invariantهای نزدیک به مدل
- `policies.py`: مجوزهای متمرکز و قابل استفاده در چند اپ
- `services.py`: عملیات تغییردهنده و تراکنشی کسب‌وکار
- `views.py`: دریافت HTTP، فراخوانی policy/service و ساخت response
- `admin.py`: orchestration پنل مدیریت و فراخوانی همان serviceها
- `signals.py`: فاقد محاسبات سنگین؛ side effectهای پنهان حذف شده‌اند

## تغییرهای اصلی

- ثبت‌نام، ظرفیت، پیشرفت، نظر و امتیاز دوره به `courses/services.py` منتقل شدند.
- دسترسی دوره در `courses/policies.py` متمرکز شد.
- چرخهٔ تلاش آزمون و نمره‌دهی تراکنشی به `quiz/services.py` منتقل شد.
- مجوز آزمون در `quiz/policies.py` متمرکز و دسترسی استاد به همان دوره محدود شد.
- ساخت پیام و اعلان چت به `chat/services.py` و مجوزها به `chat/policies.py` منتقل شدند.
- signalهای سنگین ثبت‌نام و امتیاز حذف شدند.
- constraintها و indexهای دیتابیس با migration جدید افزوده شدند.
- ارسال، فعال‌سازی و بازیابی مبتنی بر ایمیل حذف شده است؛ حساب فعلاً مستقیم فعال می‌شود.
- هیچ پیاده‌سازی SMS اضافه نشده و فقط محل آن برای نسخهٔ بعدی در توضیحات ثبت شده است.

## جریان ثبت‌نام

`courses.views.enroll_course` → `courses.services.enroll_student` → transaction و lock دوره → ساخت Enrollment → همگام‌سازی آمار

## جریان آزمون

`quiz.views.take_quiz` → policy دسترسی → `get_or_create_open_attempt` → `finalize_attempt` با lock و idempotency

## جریان چت

`chat.views.post_message` → policy دسترسی → `create_course_message` → ذخیرهٔ پیام و اعلان batch
