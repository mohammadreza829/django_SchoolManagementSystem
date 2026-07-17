"""فرم‌های ثبت‌نام، ویرایش حساب و پروفایل و تغییر رمز عبور را همراه با اعتبارسنجی ورودی تعریف می‌کند.

 
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    UserCreationForm,
    UserChangeForm,
    PasswordChangeForm,
)
from .models import Profile

User = get_user_model()


# ==================== ۱. فرم ثبت‌نام دانش‌آموز (عمومی) ====================
class StudentSignUpForm(UserCreationForm):
    """مسئولیت‌ها و رفتارهای مربوط به «StudentSignUpForm» را در این بخش کپسوله می‌کند."""
    first_name = forms.CharField(
        max_length=50,
        label="نام",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        max_length=50,
        label="نام خانوادگی",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="ایمیل", widget=forms.EmailInput(attrs={"class": "form-control"})
    )
    phone = forms.CharField(
        max_length=13,
        label="شماره تماس",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    national_code = forms.CharField(
        max_length=10,
        label="کد ملی",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta(UserCreationForm.Meta):
        """تنظیمات متادیتا، ترتیب، نام نمایشی و محدودیت‌های این مدل یا فرم را تعریف می‌کند."""
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "national_code",
        )



    def clean_national_code(self):
        """یکتایی کد ملی را بررسی و مقدار پاک‌سازی‌شده را برمی‌گرداند."""
        national_code = self.cleaned_data.get("national_code")
        user = self.instance
        # اگر کد ملی تغییر کرده باشد و برای کاربر دیگری ثبت شده باشد، خطا بده
        if User.objects.exclude(pk=user.pk).filter(national_code=national_code).exists():
            raise forms.ValidationError("این کد ملی قبلاً توسط کاربر دیگری ثبت شده است.")
        return national_code

    def clean_phone(self):
        """یکتایی و قالب شمارهٔ تلفن ایرانی را اعتبارسنجی می‌کند."""
        phone = self.cleaned_data.get("phone")
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("این شماره تماس قبلاً ثبت شده است.")
        # اعتبارسنجی فرمت شماره ایران
        if not phone.startswith("09") or len(phone) != 11:
            raise forms.ValidationError("شماره تماس باید با 09 شروع شود و 11 رقم باشد.")
        return phone

    def save(self, commit=True):
        """دادهٔ اعتبارسنجی‌شده را با اعمال قواعد تکمیلی مدل ذخیره می‌کند."""
        user = super().save(commit=False)
        user.role = "student"  
        if commit:
            user.save()
        return user


# ==================== ۲. فرم ویرایش اطلاعات پایه کاربر (همه نقش‌ها) ====================
class UserUpdateForm(forms.ModelForm):
    """مسئولیت‌ها و رفتارهای مربوط به «UserUpdateForm» را در این بخش کپسوله می‌کند."""
    class Meta:
        """تنظیمات متادیتا، ترتیب، نام نمایشی و محدودیت‌های این مدل یا فرم را تعریف می‌کند."""
        model = User
        fields = ["first_name", "last_name", "email", "national_code", "phone"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "national_code": forms.TextInput(
                attrs={"class": "form-control", "readonly": "readonly"}
            ),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
        }


# ==================== ۳. فرم ویرایش پروفایل عمومی ====================
class ProfileUpdateForm(forms.ModelForm):
    """مسئولیت‌ها و رفتارهای مربوط به «ProfileUpdateForm» را در این بخش کپسوله می‌کند."""
    class Meta:
        """تنظیمات متادیتا، ترتیب، نام نمایشی و محدودیت‌های این مدل یا فرم را تعریف می‌کند."""
        model = Profile
        fields = [
            "bio",
            "avatar",
            "cover_image",
            "gender",
            "birth_date",
            "website",
            "location",
            "twitter",
            "instagram",
            "linkedin",
            "github",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "cover_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "gender": forms.Select(attrs={"class": "form-select"}),
            "birth_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "website": forms.URLInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "twitter": forms.TextInput(attrs={"class": "form-control"}),
            "instagram": forms.TextInput(attrs={"class": "form-control"}),
            "linkedin": forms.TextInput(attrs={"class": "form-control"}),
            "github": forms.TextInput(attrs={"class": "form-control"}),
        }


# ==================== ۴. فرم تغییر رمز عبور ====================
class CustomPasswordChangeForm(PasswordChangeForm):
    """مسئولیت‌ها و رفتارهای مربوط به «CustomPasswordChangeForm» را در این بخش کپسوله می‌کند."""
    def __init__(self, *args, **kwargs):
        """شیء را مقداردهی اولیه می‌کند و تنظیمات لازم را روی فیلدها اعمال می‌کند."""
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})
