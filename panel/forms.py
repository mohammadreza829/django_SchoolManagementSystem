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
    class Meta:
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
    class Meta:
        model = Quiz
        fields = [
            "title",
            "description",
            "course",
            "time_limit_minutes",
            "pass_mark",
            "max_attempts",
            "shuffle_questions",
            "show_solution",
            "is_published",
        ]


class QuestionForm(StyleMixin, forms.ModelForm):
    class Meta:
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
    class Meta:
        model = Choice
        fields = ["text", "is_correct", "order"]


ChoiceFormSet = inlineformset_factory(
    Question, Choice, form=ChoiceForm, extra=4, can_delete=True
)
