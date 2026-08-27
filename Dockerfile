# ============================================================
#  ایمیج پایه: پایتون ۳٫۱۲ نسخهٔ slim (سبک)
# ============================================================
FROM python:3.12-slim

# PYTHONDONTWRITEBYTECODE: تولید نشدن فایل‌های .pyc
# PYTHONUNBUFFERED: نمایش بلادرنگ لاگ‌ها (مهم برای دیدن خطاها)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# پوشهٔ کاری داخل کانتینر
WORKDIR /app

# ترفند کش داکر: اول فقط requirements را کپی و نصب می‌کنیم.
# تا وقتی این فایل عوض نشود، داکر نصب مجدد را رد می‌کند و build سریع‌تر می‌شود.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# حالا کل کد پروژه را کپی می‌کنیم
COPY . .

# پورتی که gunicorn روی آن گوش می‌دهد
EXPOSE 8000

# اجرای پیش‌فرض (در docker-compose بازنویسی می‌شود)
CMD ["gunicorn", "EduPlatform.wsgi:application", "--bind", "0.0.0.0:8000"]
