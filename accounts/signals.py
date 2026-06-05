from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Profile, StudentProfile, TeacherProfile

User = get_user_model()


@receiver(post_save, sender=User)
def sync_user_profiles(sender, instance, created, **kwargs):
    """
    فقط هنگام ایجاد کاربر جدید، پروفایل‌ها را بساز.
    برای به‌روزرسانی‌های بعدی (تغییر نقش) کاری نکن تا اطلاعات از دست نرود.
    """
    # پروفایل عمومی برای همه کاربران (حتی اگر وجود داشته باشد، کاری نمی‌کند)
    Profile.objects.get_or_create(user=instance)

    if not created:
        # اگر کاربر از قبل وجود داشته، از ساخت/حذف پروفایل اختصاصی صرف نظر کن
        return

    # فقط برای کاربران تازه ساخته شده
    if instance.role == "student":
        StudentProfile.objects.get_or_create(
            user=instance,
            defaults={
                "student_id": f"STU{instance.id:05d}",
                "entry_year": 1403,
            },
        )
    elif instance.role == "teacher":
        TeacherProfile.objects.get_or_create(
            user=instance,
            defaults={
                "specialty": "عمومی",
                "degree": "کارشناسی",
            },
        )
