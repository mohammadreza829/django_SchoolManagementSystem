"""سیاست دسترسی و مدیریت پیام‌های چت دوره را متمرکز می‌کند."""

from courses.policies import has_course_access, is_course_teacher


def can_access_course_chat(user, course):
    """مشخص می‌کند کاربر اجازهٔ ورود به چت همان دوره را دارد یا نه."""
    return has_course_access(user, course)


def can_delete_course_message(user, message):
    """حذف پیام را فقط برای فرستنده یا استاد همان دوره مجاز می‌کند."""
    return bool(
        user.is_authenticated
        and (
            message.sender_id == user.id
            or is_course_teacher(user, message.course)
        )
    )
