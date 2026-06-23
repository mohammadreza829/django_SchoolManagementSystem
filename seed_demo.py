# -*- coding: utf-8 -*-
"""
seed_demo.py  —  پر کردن دیتابیس با حجم زیادی داده‌ی واقعی برای تست
==================================================================
این اسکریپت همه‌ی بخش‌های سایت را با داده‌ی نمونه‌ی فارسیِ واقع‌گرایانه پر می‌کند:

  • کاربران (مدیر، استاد، دانش‌آموز) + پروفایل‌ها (خودکار با سیگنال)
  • دسته‌بندی‌ها (والد و زیرشاخه)
  • دوره‌ها + جلسات + ضمیمه‌ها
  • ثبت‌نام‌ها + پیشرفت جلسات
  • امتیاز و نظر دوره‌ها (rating)
  • نظر و لایک جلسات
  • موضوعات، بانک سوال، گزینه‌ها
  • آزمون‌ها + اتصال سوالات
  • تلاش‌های دانش‌آموزان (تصحیح‌شده، برای پر شدن نمودارها)
  • پیام‌های چت‌روم دوره‌ها
  • اعلان‌ها (Notifications)

نحوه اجرا (از پوشه‌ای که manage.py در آن است):
    python seed_demo.py
    python seed_demo.py --fresh     # اول داده‌ی نمونه را پاک می‌کند بعد می‌سازد

دوباره‌اجرا امن است (idempotent): داده‌ی تکراری ساخته نمی‌شود.
رمز عبور همه‌ی کاربرهای نمونه: demo12345
"""

import os
import sys
import random
from datetime import timedelta

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EduPlatform.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify
from django.db import transaction

from accounts.models import Notification
from courses.models import (
    Category, Course, Lesson, LessonProgress, LessonAttachment,
    CourseRating, LessonComment, LessonLike,
)
from Enrollment.models import Enrollment
from quiz.models import (
    Topic, Question, Choice, Quiz, QuizQuestion, QuizAttempt, AttemptAnswer,
)
from chat.models import CourseMessage

User = get_user_model()
random.seed(1403)

PASSWORD = "demo12345"
now = timezone.now()

# شمارنده‌های یکتا برای کد ملی / تلفن
_nc = [1100000000]
_ph = [10000]


def next_national_code():
    _nc[0] += 1
    return str(_nc[0])


def next_phone():
    _ph[0] += 1
    return f"0912{_ph[0]:07d}"


def log(msg):
    print("  " + msg)


def days_ago(d):
    return now - timedelta(days=d)


# ============================================================ داده‌های خام
FIRST_NAMES = [
    "علی", "محمد", "رضا", "حسین", "امیر", "مهدی", "سعید", "یاسر", "کاوه", "آرش",
    "بهنام", "پویا", "سینا", "نیما", "کیان", "بابک", "فرهاد", "مازیار", "شهاب", "احسان",
    "زهرا", "فاطمه", "مریم", "نگین", "سارا", "الهام", "نازنین", "پریسا", "شیما", "مینا",
    "هانیه", "ندا", "رویا", "بهاره", "یاسمن", "کیمیا", "دنیا", "آیدا", "ترانه", "غزل",
]
LAST_NAMES = [
    "محمدی", "حسینی", "رضایی", "کریمی", "موسوی", "احمدی", "جعفری", "قاسمی", "نجفی", "یوسفی",
    "اکبری", "صادقی", "رحیمی", "کاظمی", "حیدری", "سلطانی", "غلامی", "بابایی", "شریفی", "عباسی",
    "فلاحی", "نوری", "مرادی", "زارعی", "اسدی", "خانی", "طاهری", "بیگی", "فرهادی", "مظفری",
]
CITIES = ["تهران", "اصفهان", "شیراز", "مشهد", "تبریز", "کرج", "اهواز", "رشت", "یزد", "کرمان"]
BIOS = [
    "علاقه‌مند به برنامه‌نویسی و یادگیری مهارت‌های جدید.",
    "دانشجوی مهندسی، عاشق ریاضی و حل مسئله.",
    "در حال یادگیری توسعه‌ی وب با جنگو و ری‌اکت.",
    "به طراحی، داده و هوش مصنوعی علاقه دارم.",
    "معلم و یادگیرنده‌ی همیشگی؛ آموزش را دوست دارم.",
]

# (نام دسته‌ی والد، آیکون، [زیرشاخه‌ها])
CATEGORY_TREE = [
    ("برنامه‌نویسی", "fa-code", ["پایتون", "جاوااسکریپت", "توسعه وب", "موبایل"]),
    ("ریاضیات", "fa-square-root-variable", ["جبر", "هندسه", "حسابان", "آمار و احتمال"]),
    ("علوم پایه", "fa-flask", ["فیزیک", "شیمی", "زیست‌شناسی"]),
    ("زبان", "fa-language", ["انگلیسی", "آیلتس", "مکالمه"]),
    ("مهارت‌های نرم", "fa-people-group", ["مدیریت زمان", "سخنرانی", "کارآفرینی"]),
]

# دوره‌ها: (عنوان، دسته‌ی زیرشاخه، سطح)
COURSE_DEFS = [
    ("آموزش پایتون از صفر تا صد", "پایتون", "beginner"),
    ("پایتون پیشرفته و الگوهای طراحی", "پایتون", "advanced"),
    ("جنگو برای توسعه‌ی وب حرفه‌ای", "توسعه وب", "intermediate"),
    ("ساخت API با Django REST Framework", "توسعه وب", "advanced"),
    ("جاوااسکریپت مدرن (ES6+)", "جاوااسکریپت", "beginner"),
    ("ری‌اکت از مقدماتی تا پیشرفته", "جاوااسکریپت", "intermediate"),
    ("Next.js و رندر سمت سرور", "توسعه وب", "advanced"),
    ("برنامه‌نویسی اندروید با کاتلین", "موبایل", "intermediate"),
    ("توسعه‌ی اپ موبایل با فلاتر", "موبایل", "beginner"),
    ("الگوریتم و ساختمان داده", "پایتون", "intermediate"),
    ("جبر خطی کاربردی", "جبر", "intermediate"),
    ("حسابان ۱ — مشتق و انتگرال", "حسابان", "beginner"),
    ("هندسه‌ی تحلیلی", "هندسه", "intermediate"),
    ("آمار و احتمال مهندسی", "آمار و احتمال", "advanced"),
    ("معادلات دیفرانسیل", "حسابان", "advanced"),
    ("فیزیک پایه: مکانیک", "فیزیک", "beginner"),
    ("فیزیک ۲: الکتریسیته و مغناطیس", "فیزیک", "intermediate"),
    ("شیمی عمومی", "شیمی", "beginner"),
    ("زیست‌شناسی سلولی و مولکولی", "زیست‌شناسی", "intermediate"),
    ("گرامر کامل زبان انگلیسی", "انگلیسی", "beginner"),
    ("آمادگی آزمون آیلتس (IELTS)", "آیلتس", "advanced"),
    ("مکالمه‌ی روزمره‌ی انگلیسی", "مکالمه", "beginner"),
    ("مدیریت زمان و بهره‌وری", "مدیریت زمان", "beginner"),
    ("فن بیان و سخنرانی حرفه‌ای", "سخنرانی", "intermediate"),
    ("اصول کارآفرینی و استارتاپ", "کارآفرینی", "intermediate"),
    ("یادگیری ماشین با پایتون", "پایتون", "advanced"),
    ("تح��یل داده با pandas", "پایتون", "intermediate"),
    ("گیت و گیت‌هاب برای تیم‌ها", "توسعه وب", "beginner"),
    ("طراحی پایگاه داده و SQL", "توسعه وب", "intermediate"),
    ("امنیت وب و تست نفوذ مقدماتی", "توسعه وب", "advanced"),
    ("تایپ‌اسکریپت برای برنامه‌نویسان JS", "جاوااسکریپت", "intermediate"),
    ("ساخت بازی با یونیتی", "موبایل", "intermediate"),
    ("احتمال مهندسی پیشرفته", "آمار و احتمال", "advanced"),
    ("شیمی آلی", "شیمی", "advanced"),
    ("مبانی هوش مصنوعی", "پایتون", "intermediate"),
    ("کار با لینوکس و خط فرمان", "توسعه وب", "beginner"),
]

LESSON_TITLES = [
    "مقدمه و معرفی دوره", "نصب و راه‌اندازی محیط", "مفاهیم پایه", "اولین پروژه‌ی عملی",
    "ساختارهای کنترلی", "توابع و ماژول‌ها", "کار با داده‌ها", "مدیریت خطاها",
    "پروژه‌ی میانی", "مباحث پیشرفته", "بهینه‌سازی و بهترین شیوه‌ها", "پروژه‌ی نهایی",
    "جمع‌بندی و مسیر یادگیری", "تمرین‌های تکمیلی",
]
ARTICLE_BODY = (
    "در این جلسه با مفاهیم اصلی آشنا می‌شویم و قدم‌به‌قدم پیش می‌رویم. "
    "ابتدا تعاریف را مرور می‌کنیم، سپس با چند مثال عملی موضوع را جا می‌اندازیم "
    "و در پایان یک تمرین برای تثبیت یادگیری خواهید داشت."
)
RATING_COMMENTS = [
    "دوره‌ی فوق‌العاده‌ای بود، خیلی روان توضیح داده شد.",
    "محتوا خوب بود ولی جا داشت مثال‌های بیشتری بزنه.",
    "یکی از بهترین دوره‌هایی که دیدم. ممنون از استاد.",
    "به‌دردبخور و کاربردی، پیشنهاد می‌کنم.",
    "سطح دوره عالی بود، فقط صدای ویدیوها می‌تونست بهتر باشه.",
    "خیلی چیزا یاد گرفتم، مرسی.",
    "نسبت به قیمتش واقعاً ارزش داشت.",
]
LESSON_COMMENTS = [
    "این قسمت رو چند بار دیدم، خیلی کمک کرد.",
    "ببخشید، دقیقه‌ی ۷ رو میشه بیشتر توضیح بدید؟",
    "عالی بود، دستتون درد نکنه.",
    "من اینجا به ارور خوردم، کسی راه‌حل داره؟",
    "تمرین این جلسه رو انجام دادم، خیلی خوب بود.",
]
CHAT_STUDENT_MSGS = [
    "سلام، تمرین جلسه‌ی سوم رو از کجا دانلود کنیم؟",
    "استاد ممنون بابت دوره‌ی خوبتون 🙏",
    "کسی فایل اسلایدها رو داره؟",
    "من جلسه‌ی آخر یه سوال داشتم، میشه راهنمایی کنید؟",
    "چقدر طول می‌کشه دوره رو کامل کنیم؟",
    "خیلی مطالب کاربردی بود، مرسی از همگی.",
    "برای پروژه‌ی نهایی چه ابزاری پیشنهاد می‌دید؟",
]
CHAT_TEACHER_MSGS = [
    "سلام به همه. فایل تمرین‌ها در بخش ضمیمه‌ی جلسه‌ها قرار گرفت ✅",
    "یادتون نره آزمون این هفته تا جمعه بازه.",
    "سوالاتتون رو همینجا بپرسید، در اولین فرصت جواب می‌دم.",
    "جلسه‌ی جدید آپلود شد، حتماً ببینید.",
]
SPECIALTIES = [
    "مهندسی نرم‌افزار", "علوم کامپیوتر", "ریاضی محض", "فیزیک", "شیمی",
    "زیست‌شناسی", "زبان انگلیسی", "مدیریت و کارآفرینی", "هوش مصنوعی", "امنیت سایبری",
]
DEGREES = ["کارشناسی", "کارشناسی ارشد", "دکتری"]


# ============================================================ [1] کاربران
def seed_admins():
    admins = []
    if not User.objects.filter(username="admin").exists():
        a = User.objects.create_superuser(
            username="admin", email="admin@edupro.ir", password=PASSWORD,
            first_name="مدیر", last_name="کل", national_code=next_national_code(),
            phone=next_phone(),
        )
        admins.append(a)
    else:
        admins.append(User.objects.get(username="admin"))
    return admins


def seed_teachers(n=10):
    teachers = []
    for i in range(1, n + 1):
        uname = f"teacher{i:02d}"
        u = User.objects.filter(username=uname).first()
        if not u:
            fn = random.choice(FIRST_NAMES)
            ln = random.choice(LAST_NAMES)
            u = User.objects.create_user(
                username=uname, email=f"{uname}@edupro.ir", password=PASSWORD,
                role="teacher", first_name=fn, last_name=ln,
                national_code=next_national_code(), phone=next_phone(),
                date_joined=days_ago(random.randint(200, 700)),
            )
            tp = u.teacher_profile
            tp.specialty = SPECIALTIES[(i - 1) % len(SPECIALTIES)]
            tp.degree = random.choice(DEGREES)
            tp.save()
            p = u.profile
            p.bio = random.choice(BIOS)
            p.location = random.choice(CITIES)
            p.gender = random.choice(["male", "female"])
            p.save()
        teachers.append(u)
    return teachers


def seed_students(n=60):
    students = []
    for i in range(1, n + 1):
        uname = f"student{i:03d}"
        u = User.objects.filter(username=uname).first()
        if not u:
            fn = random.choice(FIRST_NAMES)
            ln = random.choice(LAST_NAMES)
            u = User.objects.create_user(
                username=uname, email=f"{uname}@gmail.com", password=PASSWORD,
                role="student", first_name=fn, last_name=ln,
                national_code=next_national_code(), phone=next_phone(),
                date_joined=days_ago(random.randint(1, 365)),
            )
            p = u.profile
            p.bio = random.choice(BIOS)
            p.location = random.choice(CITIES)
            p.gender = random.choice(["male", "female", "other"])
            p.save()
        students.append(u)
    return students


# ============================================================ [2] دسته‌بندی‌ها
def seed_categories():
    leaf_map = {}
    order = 0
    for parent_name, icon, subs in CATEGORY_TREE:
        order += 1
        # جستجو بر اساس name (که یکتاست) تا با داده‌ی قبلی هم هماهنگ باشد
        parent, _ = Category.objects.get_or_create(
            name=parent_name,
            defaults={
                "slug": unique_slug(Category, parent_name),
                "icon": icon, "order": order, "is_active": True,
            },
        )
        for j, sub in enumerate(subs, 1):
            child, _ = Category.objects.get_or_create(
                name=sub,
                defaults={
                    "slug": unique_slug(Category, sub),
                    "parent": parent, "icon": icon,
                    "order": j, "is_active": True,
                },
            )
            leaf_map[sub] = child
    return leaf_map


# ============================================================ [3] دوره‌ها + جلسات
def unique_slug(model, base):
    base = slugify(base, allow_unicode=True) or "item"
    slug = base
    i = 1
    while model.objects.filter(slug=slug).exists():
        i += 1
        slug = f"{base}-{i}"
    return slug


def seed_courses(teachers, leaf_map):
    courses = []
    for idx, (title, cat_name, level) in enumerate(COURSE_DEFS):
        existing = Course.objects.filter(title=title).first()
        if existing:
            courses.append(existing)
            continue

        category = leaf_map.get(cat_name)
        price = random.choice([0, 0, 290000, 390000, 590000, 790000, 1200000, 1900000])
        discount = random.choice([0, 0, 0, 10, 20, 30, 50])
        capacity = random.choice([0, 0, 30, 50, 100])
        course = Course.objects.create(
            title=title,
            slug=unique_slug(Course, title),
            description=(
                f"در دوره‌ی «{title}» قدم‌به‌قدم و با پروژه‌های واقعی این مهارت را "
                "یاد می‌گیرید. این دوره برای کسانی طراحی شده که می‌خواهند از پایه شروع "
                "کنند و تا سطح حرفه‌ای پیش بروند."
            ),
            short_description=f"یادگیری کامل {title} با تمرین و پروژه‌ی عملی.",
            level=level,
            status="published",
            price=price,
            discount_percent=discount,
            duration_hours=random.randint(8, 60),
            capacity=capacity,
            category=category,
            published_at=days_ago(random.randint(10, 300)),
            view_count=random.randint(50, 5000),
        )
        # ۱ تا ۲ استاد
        chosen = random.sample(teachers, random.randint(1, 2))
        course.teachers.set(chosen)

        # جلسات
        n_lessons = random.randint(6, 14)
        total_minutes = 0
        for o in range(1, n_lessons + 1):
            ltitle = LESSON_TITLES[(o - 1) % len(LESSON_TITLES)]
            ctype = random.choice(["video", "video", "video", "article"])
            dur = random.randint(6, 35)
            total_minutes += dur
            lesson = Lesson.objects.create(
                course=course,
                title=f"جلسه {o}: {ltitle}",
                slug=f"lesson-{course.id}-{o}",
                order=o,
                content_type=ctype,
                video_url=("https://www.aparat.com/v/demo" if ctype == "video" else ""),
                article_content=(ARTICLE_BODY if ctype == "article" else ""),
                is_free_preview=(o <= 2),
                duration_minutes=dur,
                view_count=random.randint(0, 800),
            )
            # یک ضمیمه برای بعضی جلسه‌ها (بدون فایل واقعی؛ فقط رکورد)
            if random.random() < 0.3:
                LessonAttachment.objects.create(
                    lesson=lesson,
                    title=f"جزوه‌ی {ltitle}",
                    file="courses/attachments/demo.pdf",
                    is_free=lesson.is_free_preview,
                )
        course.total_lessons = n_lessons
        course.duration_hours = max(course.duration_hours, total_minutes // 60 + 1)
        course.save(update_fields=["total_lessons", "duration_hours"])
        courses.append(course)
    return courses


# ============================================================ [4] ثبت‌نام + پیشرفت
def seed_enrollments(students, courses):
    for student in students:
        k = random.randint(3, 9)
        for course in random.sample(courses, min(k, len(courses))):
            # رعایت تقریبی ظرفیت
            if course.capacity and course.active_enroll_count >= course.capacity:
                continue
            enr, created = Enrollment.objects.get_or_create(
                student=student, course=course,
                defaults={
                    "status": random.choice(["active", "active", "active", "completed"]),
                    "payment_status": "free" if course.is_free else random.choice(["paid", "paid", "pending"]),
                    "price_paid": 0 if course.is_free else course.final_price,
                    "progress_percentage": random.choice([0, 10, 25, 40, 60, 80, 100]),
                    "enrolled_at": days_ago(random.randint(1, 250)),
                },
            )
            if not created:
                continue
            if enr.status == "completed":
                enr.progress_percentage = 100
                enr.completed_at = now
                enr.save(update_fields=["progress_percentage", "completed_at"])

            # پیشرفت جلسه‌ها متناسب با درصد پیشرفت
            lessons = list(course.lessons.all())
            done = int(len(lessons) * enr.progress_percentage / 100)
            for li, lesson in enumerate(lessons):
                completed = li < done
                LessonProgress.objects.get_or_create(
                    lesson=lesson, user=student,
                    defaults={
                        "is_completed": completed,
                        "completed_at": now if completed else None,
                        "completion_percentage": 100 if completed else random.choice([0, 20, 50]),
                        "watch_count": random.randint(1, 4) if completed else random.randint(0, 1),
                    },
                )

    # به‌روزرسانی شمارنده‌ها
    for course in courses:
        course.enroll_count = course.active_enroll_count
        course.update_is_full()
        course.save(update_fields=["enroll_count"])


# ============================================================ [5] امتیاز و نظر
def seed_ratings(courses):
    for course in courses:
        enrolled = list(course.students.all())
        if not enrolled:
            continue
        raters = random.sample(enrolled, min(len(enrolled), random.randint(2, 12)))
        for user in raters:
            CourseRating.objects.get_or_create(
                course=course, user=user,
                defaults={
                    "score": random.choice([3, 4, 4, 5, 5, 5]),
                    "comment": random.choice(RATING_COMMENTS),
                    "created_at": days_ago(random.randint(1, 120)),
                },
            )
        ratings = list(course.ratings.all())
        if ratings:
            course.rating_count = len(ratings)
            course.rating_avg = round(sum(r.score for r in ratings) / len(ratings), 2)
            course.save(update_fields=["rating_count", "rating_avg"])


# ============================================================ [6] نظر/لایک جلسات
def seed_lesson_engagement(courses):
    for course in courses:
        enrolled = list(course.students.all())
        if not enrolled:
            continue
        for lesson in course.lessons.all()[:4]:
            for user in random.sample(enrolled, min(len(enrolled), random.randint(0, 4))):
                LessonComment.objects.get_or_create(
                    lesson=lesson, user=user, parent=None,
                    text=random.choice(LESSON_COMMENTS),
                )
                if random.random() < 0.6:
                    LessonLike.objects.get_or_create(lesson=lesson, user=user)


# ============================================================ [7] بانک سوال
TOPIC_TREE = [
    ("برنامه‌نویسی پایتون", ["مبانی پایتون", "توابع", "شیءگرایی"]),
    ("ریاضی", ["جبر", "حسابان", "احتمال"]),
    ("عمومی", ["دانش عمومی"]),
]

# هر تاپل: (متن، نوع، سطح، بارم، گزینه‌ها[(متن,درست)] یا جواب)
QUESTION_BANK = {
    "مبانی پایتون": [
        ("خروجی print(2 ** 3) چیست؟", "single", "easy", 1,
         [("6", False), ("8", True), ("9", False), ("23", False)]),
        ("کدام نوع داده در پایتون تغییرناپذیر (immutable) است؟", "single", "medium", 2,
         [("list", False), ("dict", False), ("tuple", True), ("set", False)]),
        ("عبارت 'len' یک تابع داخلی پایتون است.", "truefalse", "easy", 1,
         [("درست", True), ("نادرست", False)]),
    ],
    "توابع": [
        ("کلمه‌ی کلیدی تعریف تابع در پایتون چیست؟", "single", "easy", 1,
         [("function", False), ("def", True), ("func", False), ("lambda", False)]),
        ("کدام‌ها روش ارسال آرگومان به تابع هستند؟ (چندگزینه‌ای)", "multiple", "medium", 2,
         [("موقعیتی (positional)", True), ("کلیدواژه‌ای (keyword)", True),
          ("رنگی", False), ("پیش‌فرض (default)", True)]),
    ],
    "شیءگرایی": [
        ("متد سازنده در کلاس‌های پایتون چه نام دارد؟", "short", "medium", 2, "__init__"),
        ("وراثت یکی از اصول شیءگرایی است.", "truefalse", "easy", 1,
         [("درست", True), ("نادرست", False)]),
    ],
    "جبر": [
        ("اگر x + 5 = 12 باشد، x چند است؟", "numeric", "easy", 1, 7.0),
        ("ریشه‌های معادله‌ی x^2 - 9 = 0 کدام‌اند؟", "multiple", "medium", 2,
         [("3", True), ("-3", True), ("9", False), ("0", False)]),
    ],
    "حسابان": [
        ("مشتق تابع f(x)=x^2 برابر است با:", "single", "medium", 2,
         [("x", False), ("2x", True), ("x^2", False), ("2", False)]),
        ("حد مقدار sin(x)/x وقتی x به صفر میل می‌کند چند است؟", "numeric", "hard", 3, 1.0),
    ],
    "احتمال": [
        ("احتمال آمدن شیر در پرتاب یک سکه‌ی سالم چقدر است؟", "numeric", "easy", 1, 0.5),
        ("در پرتاب یک تاس، احتمال عدد زوج چند است؟", "numeric", "medium", 2, 0.5),
    ],
    "دانش عمومی": [
        ("پایتخت ایران کدام شهر است؟", "short", "easy", 1, "تهران"),
        ("بزرگ‌ترین سیاره‌ی منظومه‌ی شمسی کدام است؟", "single", "easy", 1,
         [("زمین", False), ("مشتری", True), ("مریخ", False), ("زحل", False)]),
    ],
}


def seed_question_bank(admins, teachers):
    topic_map = {}
    for parent_name, subs in TOPIC_TREE:
        parent, _ = Topic.objects.get_or_create(name=parent_name)
        for j, sub in enumerate(subs, 1):
            child, _ = Topic.objects.get_or_create(name=sub, defaults={"parent": parent, "order": j})
            topic_map[sub] = child

    creator = (teachers or admins)[0]
    questions_by_topic = {}
    for topic_name, qlist in QUESTION_BANK.items():
        topic = topic_map.get(topic_name)
        if not topic:
            continue
        bucket = questions_by_topic.setdefault(topic_name, [])
        for qtext, qtype, diff, pts, payload in qlist:
            q = Question.objects.filter(text=qtext).first()
            if not q:
                q = Question.objects.create(
                    topic=topic, text=qtext, question_type=qtype,
                    difficulty=diff, points=pts, created_by=creator,
                )
                if qtype in ("single", "multiple", "truefalse"):
                    for oi, (otext, correct) in enumerate(payload, 1):
                        Choice.objects.create(question=q, text=otext, is_correct=correct, order=oi)
                elif qtype == "numeric":
                    q.correct_numeric = float(payload)
                    q.numeric_tolerance = 0.01
                    q.save(update_fields=["correct_numeric", "numeric_tolerance"])
                elif qtype == "short":
                    q.correct_text = str(payload)
                    q.save(update_fields=["correct_text"])
            bucket.append(q)
    return questions_by_topic


# ============================================================ [8] آزمون‌ها
def seed_quizzes(courses, questions_by_topic, teachers, admins):
    all_questions = [q for lst in questions_by_topic.values() for q in lst]
    quizzes = []
    creator = (teachers or admins)[0]
    # به حدود نیمی از دوره‌ها آزمون وصل می‌کنیم
    target_courses = courses[::2]
    for course in target_courses:
        title = f"آزمون پایان دوره — {course.title}"
        quiz = Quiz.objects.filter(title=title).first()
        if not quiz:
            teacher = course.teachers.first() or creator
            quiz = Quiz.objects.create(
                title=title,
                slug=unique_slug(Quiz, title),
                description="این آزمون میزان یادگیری شما از این دوره را می‌سنجد.",
                course=course,
                time_limit_minutes=random.choice([0, 15, 20, 30]),
                pass_mark=50,
                max_attempts=random.choice([0, 1, 3]),
                shuffle_questions=random.choice([True, False]),
                show_solution=True,
                is_published=True,
                created_by=teacher,
            )
            picked = random.sample(all_questions, min(len(all_questions), random.randint(5, 8)))
            for o, q in enumerate(picked, 1):
                QuizQuestion.objects.get_or_create(quiz=quiz, question=q, defaults={"order": o})
        quizzes.append(quiz)
    return quizzes


# ============================================================ [9] تلاش‌ها
def _answer_question(attempt, q, make_correct):
    """یک پاسخ برای سوال می‌سازد و تصحیح می‌کند."""
    ans, created = AttemptAnswer.objects.get_or_create(attempt=attempt, question=q)
    if not created:
        return
    if q.is_choice_based:
        correct_choices = list(q.choices.filter(is_correct=True))
        wrong_choices = list(q.choices.filter(is_correct=False))
        if make_correct and correct_choices:
            ans.selected_choices.set(correct_choices)
        else:
            if wrong_choices:
                ans.selected_choices.set(random.sample(wrong_choices, 1))
            elif correct_choices:
                ans.selected_choices.set([correct_choices[0]])
    elif q.question_type == "numeric":
        if make_correct and q.correct_numeric is not None:
            ans.answer_text = str(q.correct_numeric)
        else:
            ans.answer_text = str((q.correct_numeric or 0) + random.choice([1, 2, -1, 3]))
    elif q.question_type == "short":
        ans.answer_text = q.correct_text if make_correct else "پاسخ نادرست"
    ans.save()
    ans.grade()


def seed_attempts(quizzes):
    for quiz in quizzes:
        if not quiz.course:
            continue
        students = list(quiz.course.students.all())
        if not students:
            continue
        questions = quiz.get_questions()
        if not questions:
            continue
        takers = random.sample(students, min(len(students), random.randint(2, 10)))
        for student in takers:
            # اگر قبلاً تلاش کامل داشته، رد شو (idempotent تقریبی)
            if QuizAttempt.objects.filter(quiz=quiz, student=student, status="completed").exists():
                continue
            attempt = QuizAttempt.objects.create(
                quiz=quiz, student=student, status="in_progress",
            )
            # احتمال درست‌بودن هر پاسخ برای این دانش‌آموز
            skill = random.uniform(0.35, 0.95)
            for q in questions:
                _answer_question(attempt, q, make_correct=(random.random() < skill))
            attempt.calculate_score()
            attempt.started_at = days_ago(random.randint(1, 90))
            attempt.save(update_fields=["started_at"])


# ============================================================ [10] چت‌روم
def seed_chat(courses):
    for course in courses:
        if CourseMessage.objects.filter(course=course).exists():
            continue
        teacher = course.teachers.first()
        students = list(course.students.all())
        if not teacher or not students:
            continue
        # چند پیام رفت‌وبرگشتی
        n = random.randint(4, 10)
        for k in range(n):
            if k == 0 or random.random() < 0.3:
                sender = teacher
                text = random.choice(CHAT_TEACHER_MSGS)
                ann = True
            else:
                sender = random.choice(students)
                text = random.choice(CHAT_STUDENT_MSGS)
                ann = False
            CourseMessage.objects.create(
                course=course, sender=sender, text=text, is_announcement=ann,
            )


# ============================================================ [11] اعلان‌ها
NOTIF_MSGS = [
    "به پلتفرم آموزشی خوش آمدید! 🎉",
    "دوره‌ی جدیدی در حوزه‌ی موردعلاقه‌ی شما منتشر شد.",
    "یک پیام جدید در چت‌روم دوره دارید.",
    "آزمون پایان دوره برای شما فعال شد.",
    "تخفیف ویژه‌ی این هفته را از دست ندهید!",
]


def seed_notifications(users):
    for user in users:
        if Notification.objects.filter(user=user).exists():
            continue
        for _ in range(random.randint(1, 4)):
            Notification.objects.create(
                user=user,
                message=random.choice(NOTIF_MSGS),
                is_read=random.choice([True, False, False]),
            )


# ============================================================ پاک‌سازی اختیاری
def fresh_wipe():
    print("[!] حذف داده‌ی نمونه‌ی قبلی...")
    AttemptAnswer.objects.all().delete()
    QuizAttempt.objects.all().delete()
    QuizQuestion.objects.all().delete()
    Quiz.objects.all().delete()
    Choice.objects.all().delete()
    Question.objects.all().delete()
    Topic.objects.all().delete()
    CourseMessage.objects.all().delete()
    LessonLike.objects.all().delete()
    LessonComment.objects.all().delete()
    LessonProgress.objects.all().delete()
    CourseRating.objects.all().delete()
    LessonAttachment.objects.all().delete()
    Lesson.objects.all().delete()
    Enrollment.objects.all().delete()
    Course.objects.all().delete()
    Category.objects.all().delete()
    Notification.objects.all().delete()
    # کاربرهای نمونه را پاک کن (سوپریوزرها بمانند)
    User.objects.filter(username__startswith="teacher").delete()
    User.objects.filter(username__startswith="student").delete()


# ============================================================ اجرا
@transaction.atomic
def run():
    print("=" * 60)
    print("شروع پر کردن دیتابیس با داده‌های نمونه...")
    print("=" * 60)

    if "--fresh" in sys.argv:
        fresh_wipe()

    print("[1] کاربران...")
    admins = seed_admins()
    teachers = seed_teachers(10)
    students = seed_students(60)
    log(f"مدیر: {len(admins)} | استاد: {len(teachers)} | دانش‌آموز: {len(students)}")

    print("[2] دسته‌بندی‌ها...")
    leaf_map = seed_categories()
    log(f"{Category.objects.count()} دسته‌بندی")

    print("[3] دوره‌ها و جلسات...")
    courses = seed_courses(teachers, leaf_map)
    log(f"{len(courses)} دوره | {Lesson.objects.count()} جلسه")

    print("[4] ثبت‌نام‌ها و پیشرفت...")
    seed_enrollments(students, courses)
    log(f"{Enrollment.objects.count()} ثبت‌نام | {LessonProgress.objects.count()} پیشرفت جلسه")

    print("[5] امتیاز و نظر دوره‌ها...")
    seed_ratings(courses)
    log(f"{CourseRating.objects.count()} امتیاز")

    print("[6] نظر و لایک جلسات...")
    seed_lesson_engagement(courses)
    log(f"{LessonComment.objects.count()} نظر | {LessonLike.objects.count()} لایک")

    print("[7] بانک سوال...")
    questions_by_topic = seed_question_bank(admins, teachers)
    log(f"{Topic.objects.count()} موضوع | {Question.objects.count()} سوال | {Choice.objects.count()} گزینه")

    print("[8] آزمون‌ها...")
    quizzes = seed_quizzes(courses, questions_by_topic, teachers, admins)
    log(f"{len(quizzes)} آزمون")

    print("[9] تلاش‌های دانش‌آموزان...")
    seed_attempts(quizzes)
    log(f"{QuizAttempt.objects.count()} تلاش | {AttemptAnswer.objects.count()} پاسخ")

    print("[10] چت‌روم دوره‌ها...")
    seed_chat(courses)
    log(f"{CourseMessage.objects.count()} پیام")

    print("[11] اعلان‌ها...")
    seed_notifications(list(User.objects.all()))
    log(f"{Notification.objects.count()} اعلان")

    print("=" * 60)
    print("✅ تمام شد!")
    print(f"رمز عبور همه‌ی کاربرها: {PASSWORD}")
    print("نمونه ورود — مدیر: admin | استاد: teacher01 | دانش‌آموز: student001")
    print("=" * 60)


if __name__ == "__main__":
    run()
