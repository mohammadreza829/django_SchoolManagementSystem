"""قواعد متمرکز دسترسی به آزمون‌ها را تعریف می‌کند."""

from courses.policies import is_course_teacher


def is_quiz_admin(user):
    """فقط مدیر یا کارمند سامانه را دارای دسترسی سراسری آزمون می‌داند."""
    return bool(
        user.is_authenticated
        and (user.is_superuser or user.is_staff or getattr(user, "role", "") == "admin")
    )


def can_access_quiz(user, quiz):
    """مجوز مشاهده و شرکت در آزمون را با توجه به دوره بررسی می‌کند."""
    if is_quiz_admin(user):
        return True
    if quiz.course is None:
        return True
    if is_course_teacher(user, quiz.course):
        return True

    from courses.policies import has_course_access

    return has_course_access(user, quiz.course)


def bypass_quiz_schedule(user, quiz):
    """تنها مدیر یا استاد همان دوره را از بازهٔ زمانی آزمون مستثنا می‌کند."""
    if is_quiz_admin(user):
        return True
    return bool(quiz.course and is_course_teacher(user, quiz.course))
