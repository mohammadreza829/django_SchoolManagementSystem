"""فرم‌های مدیریت دوره، آزمون، سؤال و گزینه‌ها را همراه با ظاهر مشترک تعریف می‌کند.

این فایل بخشی از پروژهٔ مدرسهٔ آنلاین است و مسئولیت‌های آن عمداً در همین دامنه نگه داشته شده‌اند.
"""

# panel/forms.py
from django import forms
from django.forms import inlineformset_factory

from courses.models import Course
from quiz.models import Quiz, Question, Choice

INPUT = (
    "w-full bg-elevated border border-white/10 rounded-xl px-3 py-2 "
    "text-sm text-gray-100 focus:border-primary outline-none"
)


class StyleMixin:
    """به همه‌ی ویدجت‌ها کلاس Tailwind اضافه می‌کند تا قالب تمیز بماند."""

    def __init__(self, *args, **kwargs):
        """شیء را مقداردهی اولیه می‌کند و تنظیمات لازم را روی فیلدها اعمال می‌کند."""
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "w-5 h-5 accent-indigo-500")
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("class", INPUT + " min-h-[90px]")
                widget.attrs.setdefault("rows", 3)
            elif isinstance(widget, forms.SelectMultiple):
                widget.attrs.setdefault("class", INPUT + " min-h-[120px]")
            else:
                widget.attrs.setdefault("class", INPUT)


class CourseForm(StyleMixin, forms.ModelForm):
    """ورودی ساخت یا ویرایش دوره را دریافت و اعتبارسنجی می‌کند."""
    class Meta:
        """تنظیمات متادیتا، ترتیب، نام نمایشی و محدودیت‌های این مدل یا فرم را تعریف می‌کند."""
        model = Course
        fields = [
            "title",
            "short_description",
            "description",
            "category",
            "level",
            "status",
            "price",
            "discount_percent",
            "duration_hours",
            "thumbnail",
            "teachers",
        ]


class QuizForm(StyleMixin, forms.ModelForm):
    """ورودی ساخت یا ویرایش آزمون و محدودیت‌های زمانی آن را اعتبارسنجی می‌کند."""
    class Meta:
        """تنظیمات متادیتا، ترتیب، نام نمایشی و محدودیت‌های این مدل یا فرم را تعریف می‌کند."""
        model = Quiz
        fields = [
            "title",
            "description",
            "course",
            "time_limit_minutes",
            "pass_mark",
            "max_attempts",
            "available_from",
            "available_until",
            "shuffle_questions",
            "show_solution",
            "is_published",
        ]
        widgets = {
            "available_from": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "available_until": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }

    def __init__(self, *args, **kwargs):
        """شیء را مقداردهی اولیه می‌کند و تنظیمات لازم را روی فیلدها اعمال می‌کند."""
        super().__init__(*args, **kwargs)
        # پذیرفتن مقدار ورودیِ <input type="datetime-local">
        for name in ("available_from", "available_until"):
            self.fields[name].input_formats = [
                "%Y-%m-%dT%H:%M",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
            ]
            self.fields[name].required = False


class QuestionForm(StyleMixin, forms.ModelForm):
    """اطلاعات سؤال و پاسخ صحیح متناسب با نوع سؤال را دریافت می‌کند."""
    class Meta:
        """تنظیمات متادیتا، ترتیب، نام نمایشی و محدودیت‌های این مدل یا فرم را تعریف می‌کند."""
        model = Question
        fields = [
            "topic",
            "text",
            "question_type",
            "difficulty",
            "points",
            "correct_numeric",
            "numeric_tolerance",
            "correct_text",
            "solution",
            "is_active",
        ]


class ChoiceForm(StyleMixin, forms.ModelForm):
    """متن، صحت و ترتیب یک گزینهٔ سؤال را دریافت می‌کند."""
    class Meta:
        """تنظیمات متادیتا، ترتیب، نام نمایشی و محدودیت‌های این مدل یا فرم را تعریف می‌کند."""
        model = Choice
        fields = ["text", "is_correct", "order"]


ChoiceFormSet = inlineformset_factory(
    Question, Choice, form=ChoiceForm, extra=4, can_delete=True
)
