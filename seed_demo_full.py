"""
seed_demo_full.py
=================
اسکریپت پر کردن خودکار دیتابیس با داده‌های نمونه:
کاربران، دسته‌بندی‌ها، دوره‌ها، جلسات، ثبت‌نام‌ها، موضوعات، بانک سوال،
آزمون‌ها و چند «تلاش» شبیه‌سازی‌شده تا نمودار پیشرفت هم پر بشه.

نحوه اجرا (از پوشه‌ای که manage.py در آن است):
    python seed_demo_full.py

دوباره‌اجرا امن است (idempotent): داده‌ی تکراری ساخته نمی‌شود.
"""

import os
import django
import random

# --- بوت‌استرپ جنگو (حتماً قبل از import کردن مدل‌ها) ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EduPlatform.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone

from courses.models import Category, Course, Lesson, LessonProgress
from Enrollment.models import Enrollment
from quiz.models import (
    Topic, Question, Choice, Quiz, QuizQuestion, QuizAttempt, AttemptAnswer,
)

User = get_user_model()
random.seed(42)

PASSWORD = "demo12345"


def log(msg):
    print("    " + msg)


# ----------------------------------------------------------- [1] کاربران
def make_user(username, email, role, first, last, national_code):
    user = User.objects.filter(username=username).first()
    if user:
        return user
    return User.objects.create_user(
        username=username,
        email=email,
        password=PASSWORD,
        role=role,
        first_name=first,
        last_name=last,
        national_code=national_code,
    )


def seed_users():
    print("[1] کاربران...")
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser(
            username="admin",
            email="admin@demo.test",
            password="admin12345",
            national_code="1000000000",
            first_name="مدیر",
            last_name="سامانه",
        )
        log("سوپریوزر admin ساخته شد (رمز: admin12345)")

    teachers = [
        make_user("teacher_ali", "ali@demo.test", "teacher", "علی", "رضایی", "1000000011"),
        make_user("teacher_sara", "sara@demo.test", "teacher", "سارا", "محمدی", "1000000012"),
    ]
    student_specs = [
        ("student_reza", "reza@demo.test", "رضا", "کریمی", "1000000021"),
        ("student_mona", "mona@demo.test", "مونا", "حسینی", "1000000022"),
        ("student_amir", "amir@demo.test", "امیر", "نوری", "1000000023"),
        ("student_niloo", "niloo@demo.test", "نیلوفر", "احمدی", "1000000024"),
    ]
    students = [make_user(u, e, "student", f, l, nc) for (u, e, f, l, nc) in student_specs]
    log(str(len(teachers)) + " استاد و " + str(len(students)) + " دانش‌آموز آماده شد")
    return teachers, students


# ------------------------------------------------------ [2] دسته‌بندی‌ها
def seed_categories():
    print("[2] دسته‌بندی‌ها...")
    math, _ = Category.objects.get_or_create(
        slug="math", defaults={"name": "ریاضی"}
    )
    g8, _ = Category.objects.get_or_create(
        slug="math-grade-8", defaults={"name": "ریاضی پایه هشتم", "parent": math}
    )
    g9, _ = Category.objects.get_or_create(
        slug="math-grade-9", defaults={"name": "ریاضی پایه نهم", "parent": math}
    )
    return {"math": math, "g8": g8, "g9": g9}


# --------------------------------------------------- [3,4] دوره‌ها و جلسات
def make_course(slug, title, short, desc, teacher, category, level="beginner", price=0):
    course, created = Course.objects.get_or_create(
        slug=slug,
        defaults={
            "title": title,
            "short_description": short,
            "description": desc,
            "status": "published",
            "level": level,
            "price": price,
            "category": category,
        },
    )
    if created:
        course.teachers.set([teacher])
    return course


def make_lessons(course, titles):
    for i, t in enumerate(titles, start=1):
        Lesson.objects.get_or_create(
            course=course,
            order=i,
            defaults={
                "title": t,
                "content_type": "article",
                "article_content": "متن آموزشی درس: " + t,
                "duration_minutes": random.choice([8, 12, 15, 20]),
                "is_free_preview": (i == 1),
            },
        )
    course.total_lessons = course.lessons.count()
    course.save(update_fields=["total_lessons"])


# -------------------------------------------- [5] ثبت‌نام‌ها و پیشرفت
def seed_enrollments(students, courses):
    print("[5] ثبت‌نام‌ها و پیشرفت دروس...")
    for student in students:
        for course in courses:
            enr, _ = Enrollment.objects.get_or_create(
                student=student,
                course=course,
                defaults={"status": "active", "payment_status": "free"},
            )
            lessons = list(course.lessons.all())
            if not lessons:
                continue
            n_done = random.randint(0, len(lessons))
            for lesson in lessons[:n_done]:
                LessonProgress.objects.get_or_create(
                    lesson=lesson,
                    user=student,
                    defaults={
                        "is_completed": True,
                        "completed_at": timezone.now(),
                        "completion_percentage": 100,
                        "watch_count": 1,
                    },
                )
            enr.progress_percentage = int(n_done / len(lessons) * 100)
            enr.save(update_fields=["progress_percentage"])


# ------------------------------------------- [6,7,8] موضوعات، سوال، آزمون
def seed_quiz(teachers, courses_by_slug):
    print("[6] موضوعات و بانک سوال...")
    creator = teachers[0]
    algebra, _ = Topic.objects.get_or_create(name="جبر")
    geometry, _ = Topic.objects.get_or_create(name="هندسه")
    eq, _ = Topic.objects.get_or_create(name="معادله درجه دو", defaults={"parent": algebra})

    def mc(topic, text, options, difficulty="easy", points=1, solution="", multiple=False):
        existing = Question.objects.filter(text=text).first()
        if existing:
            return existing
        qtype = Question.MULTIPLE if multiple else Question.SINGLE
        q = Question.objects.create(
            topic=topic, text=text, question_type=qtype,
            difficulty=difficulty, points=points, solution=solution, created_by=creator,
        )
        for i, opt in enumerate(options):
            Choice.objects.create(question=q, text=opt[0], is_correct=opt[1], order=i)
        return q

    def tf(topic, text, answer_true, difficulty="easy", points=1, solution=""):
        existing = Question.objects.filter(text=text).first()
        if existing:
            return existing
        q = Question.objects.create(
            topic=topic, text=text, question_type=Question.TRUE_FALSE,
            difficulty=difficulty, points=points, solution=solution, created_by=creator,
        )
        Choice.objects.create(question=q, text="درست", is_correct=answer_true, order=0)
        Choice.objects.create(question=q, text="غلط", is_correct=not answer_true, order=1)
        return q

    def numeric(topic, text, answer, tol=0, difficulty="medium", points=2, solution=""):
        existing = Question.objects.filter(text=text).first()
        if existing:
            return existing
        return Question.objects.create(
            topic=topic, text=text, question_type=Question.NUMERIC,
            correct_numeric=answer, numeric_tolerance=tol,
            difficulty=difficulty, points=points, solution=solution, created_by=creator,
        )

    def short(topic, text, answer, difficulty="easy", points=1, solution=""):
        existing = Question.objects.filter(text=text).first()
        if existing:
            return existing
        return Question.objects.create(
            topic=topic, text=text, question_type=Question.SHORT,
            correct_text=answer, difficulty=difficulty, points=points,
            solution=solution, created_by=creator,
        )

    questions = []
    questions.append(mc(
        eq, "ریشه‌های معادله $x^2 - 5x + 6 = 0$ کدام‌اند؟",
        [("$x=2, x=3$", True), ("$x=1, x=6$", False),
         ("$x=-2, x=-3$", False), ("$x=0, x=5$", False)],
        difficulty="medium", points=2,
        solution="با تجزیه: $(x-2)(x-3)=0$ پس $x=2$ یا $x=3$.",
    ))
    questions.append(mc(
        algebra, "حاصل $2x + 3x$ کدام است؟",
        [("$5x$", True), ("$6x$", False), ("$5x^2$", False), ("$23x$", False)],
    ))
    questions.append(tf(
        algebra, "معادله $x + 2 = 5$ ریشه $x=3$ دارد.", True,
        solution="$x = 5 - 2 = 3$",
    ))
    questions.append(numeric(
        algebra, "اگر $3x = 12$ باشد، مقدار $x$ چند است؟", 4,
        solution="$x = 12 / 3 = 4$",
    ))
    questions.append(numeric(
        geometry, "مساحت مربعی به ضلع ۵ چند است؟", 25,
        solution="مساحت مربع = ضلع به توان دو = $5^2 = 25$",
    ))
    questions.append(short(
        geometry, "شکل سه‌ضلعی چه نام دارد؟", "مثلث",
    ))
    questions.append(mc(
        eq, "کدام معادله درجه دوم است؟",
        [("$x^2 + 1 = 0$", True), ("$2x + 1 = 0$", False),
         ("$x + 5 = 2$", False), ("$3 = 3$", False)],
    ))
    print("[7] " + str(len(questions)) + " سوال در بانک آماده شد")

    g8 = courses_by_slug.get("grade-8-math")
    quiz, _ = Quiz.objects.get_or_create(
        title="آزمون جبر — پایه هشتم",
        defaults={
            "description": "آزمون نمونه شامل سوالات تک‌گزینه‌ای، درست/غلط، عددی و کوتاه با پشتیبانی فرمول ریاضی.",
            "course": g8,
            "time_limit_minutes": 10,
            "pass_mark": 60,
            "max_attempts": 0,
            "show_solution": True,
            "is_published": True,
            "created_by": creator,
        },
    )
    for i, q in enumerate(questions):
        QuizQuestion.objects.get_or_create(quiz=quiz, question=q, defaults={"order": i})

    print("[8] آزمون «" + quiz.title + "» با " + str(quiz.question_count) + " سوال آماده شد")
    return quiz


# ----------------------------------------------- [9] شبیه‌سازی تلاش‌ها
def simulate_attempts(quiz, students):
    print("[9] شبیه‌سازی تلاش‌های دانش‌آموزان (تست تصحیح خودکار)...")
    skills = [0.9, 0.7, 0.5, 0.3]
    for idx, student in enumerate(students):
        skill = skills[idx % len(skills)]
        if QuizAttempt.objects.filter(quiz=quiz, student=student).exists():
            continue
        attempt = QuizAttempt.objects.create(
            quiz=quiz, student=student, max_score=quiz.total_points
        )
        for q in quiz.get_questions():
            ans = AttemptAnswer.objects.create(attempt=attempt, question=q)
            correct = random.random() < skill
            if q.is_choice_based:
                choices = list(q.choices.all())
                correct_choices = [c for c in choices if c.is_correct]
                wrong_choices = [c for c in choices if not c.is_correct]
                if correct and correct_choices:
                    ans.selected_choices.set(correct_choices)
                elif wrong_choices:
                    ans.selected_choices.set([random.choice(wrong_choices)])
            elif q.question_type == Question.NUMERIC:
                base = q.correct_numeric if q.correct_numeric is not None else 0
                ans.answer_text = str(base if correct else base + 1)
                ans.save(update_fields=["answer_text"])
            else:
                ans.answer_text = q.correct_text if correct else "نمی‌دانم"
                ans.save(update_fields=["answer_text"])
            ans.grade()
        attempt.calculate_score()
        status = "قبول" if attempt.is_passed else "مردود"
        log(student.username + ": " + str(attempt.percentage) + "% (" + status + ")")


# --------------------------------------------------------------- main
def run():
    line = "=" * 55
    print(line)
    print(" شروع پر کردن داده‌های نمونه")
    print(line)

    teachers, students = seed_users()
    cats = seed_categories()

    print("[3] دوره‌ها...")
    c1 = make_course(
        "grade-8-math", "ریاضی پایه هشتم", "آموزش کامل ریاضی هشتم",
        "دوره جامع ریاضی پایه هشتم شامل جبر و هندسه.",
        teachers[0], cats["g8"], price=0,
    )
    c2 = make_course(
        "grade-9-math", "ریاضی پایه نهم", "آموزش کامل ریاضی نهم",
        "دوره جامع ریاضی پایه نهم.",
        teachers[1], cats["g9"], level="intermediate", price=200000,
    )

    print("[4] جلسات...")
    make_lessons(c1, ["مقدمه و مرور", "عبارت‌های جبری", "معادله درجه یک", "معادله درجه دو", "هندسه مقدماتی"])
    make_lessons(c2, ["مرور پایه هشتم", "اتحادها", "عبارت‌های گویا"])

    seed_enrollments(students, [c1, c2])
    quiz = seed_quiz(teachers, {"grade-8-math": c1, "grade-9-math": c2})
    simulate_attempts(quiz, students)

    print(line)
    print(" پایان! ورود با admin / admin12345 (پنل مدیر)")
    print("        یا student_reza / demo12345 (دانش‌آموز)")
    print(line)


if __name__ == "__main__":
    run()
