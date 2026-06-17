"""
=====================================================================
  اپ کوییز (Quiz / Assessment)
=====================================================================
ساختار کلی این اپ اینه:

  Topic            → موضوع / زیرموضوع (درختی — مثل Category)
  Question         → یک سوال در بانک سوال (Question Bank)
  Choice           → گزینه‌های یک سوال چندگزینه‌ای
  Quiz             → یک آزمون (مجموعه‌ای از سوالات)
  QuizQuestion     → جدول واسط بین Quiz و Question (برای ترتیب/نمره)
  QuizAttempt      → یک بار تلاش دانش‌آموز برای دادن آزمون
  AttemptAnswer    → پاسخ دانش‌آموز به یک سوال در یک تلاش

نکته مهم: متن سوال‌ها و گزینه‌ها می‌تونن فرمول LaTeX داشته باشن
(مثلاً: $x^2 + 3x = 0$) که در تمپلیت با KaTeX رندر می‌شن.
"""

from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

# به جای import مستقیم User بهتره از settings.AUTH_USER_MODEL استفاده کنیم
User = settings.AUTH_USER_MODEL


# =====================================================================
#  1) موضوع / زیرموضوع
# =====================================================================
class Topic(models.Model):
    """
    موضوع سوالات. با parent خودارجاعی (self) می‌تونی
    درخت موضوع/زیرموضوع بسازی.
    مثال: ریاضی پایه ۸ > جبر > معادله درجه دو
    """

    name = models.CharField(max_length=120, verbose_name="نام موضوع")
    slug = models.SlugField(max_length=140, unique=True, blank=True, verbose_name="slug")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="subtopics",
        verbose_name="موضوع والد",
    )
    order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        verbose_name = "موضوع"
        verbose_name_plural = "موضوعات"
        ordering = ["order", "name"]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            # allow_unicode=True تا slug فارسی هم درست ساخته بشه
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


# =====================================================================
#  2) سوال (بانک سوال)
# =====================================================================
class Question(models.Model):
    """
    یک سوال مستقل در بانک سوال.
    هر سوال می‌تونه در چند آزمون مختلف استفاده بشه (قابلیت بازاستفاده).
    """

    # نوع سوال — روش تصحیح خودکار بر اساس همین تعیین می‌شه
    SINGLE = "single"        # تک‌گزینه‌ای (یک جواب درست)
    MULTIPLE = "multiple"    # چندگزینه‌ای (چند جواب درست)
    TRUE_FALSE = "truefalse" # درست / غلط
    NUMERIC = "numeric"      # پاسخ عددی
    SHORT = "short"          # پاسخ کوتاه متنی

    QUESTION_TYPES = (
        (SINGLE, "تک‌گزینه‌ای"),
        (MULTIPLE, "چندگزینه‌ای"),
        (TRUE_FALSE, "درست / غلط"),
        (NUMERIC, "پاسخ عددی"),
        (SHORT, "پاسخ کوتاه"),
    )

    DIFFICULTY_CHOICES = (
        ("easy", "آسان"),
        ("medium", "متوسط"),
        ("hard", "سخت"),
    )

    topic = models.ForeignKey(
        Topic,
        on_delete=models.PROTECT,   # تا با حذف موضوع، سوال‌ها پاک نشن
        related_name="questions",
        verbose_name="موضوع",
    )
    text = models.TextField(
        verbose_name="متن سوال",
        help_text="می‌تونی فرمول LaTeX بین علامت $...$ بنویسی، مثل $x^2+1=0$",
    )
    image = models.ImageField(
        upload_to="quiz/questions/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="تصویر سوال",
    )
    question_type = models.CharField(
        max_length=12, choices=QUESTION_TYPES, default=SINGLE, verbose_name="نوع سوال"
    )
    difficulty = models.CharField(
        max_length=6, choices=DIFFICULTY_CHOICES, default="medium", verbose_name="سطح سختی"
    )
    points = models.PositiveSmallIntegerField(default=1, verbose_name="بارم (نمره)")

    # پاسخ صحیح برای سوالات عددی/کوتاه (چندگزینه‌ای‌ها از Choice می‌آن)
    correct_numeric = models.FloatField(
        blank=True, null=True, verbose_name="پاسخ عددی صحیح"
    )
    numeric_tolerance = models.FloatField(
        default=0, verbose_name="خطای مجاز عددی",
        help_text="مثلاً 0.01 یعنی جواب تا ±0.01 درست حساب می‌شه",
    )
    correct_text = models.CharField(
        max_length=255, blank=True, verbose_name="پاسخ متنی صحیح"
    )

    # راه‌حل / توضیح (بعد از اتمام آزمون نشون داده می‌شه) — پشتیبانی LaTeX
    solution = models.TextField(
        blank=True, verbose_name="راه‌حل / توضیح پاسخ"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions_created",
        verbose_name="سازنده",
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "سوال"
        verbose_name_plural = "بانک سوالات"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["topic", "difficulty"]),
            models.Index(fields=["question_type"]),
        ]

    def __str__(self):
        return f"[{self.get_difficulty_display()}] {self.text[:50]}"

    @property
    def is_choice_based(self):
        """آیا این سوال گزینه‌محوره؟ (تک/چندگزینه‌ای/درست-غلط)"""
        return self.question_type in (self.SINGLE, self.MULTIPLE, self.TRUE_FALSE)


# =====================================================================
#  3) گزینه‌ها
# =====================================================================
class Choice(models.Model):
    """گزینه‌های یک سوال گزینه‌محور."""

    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="choices", verbose_name="سوال"
    )
    text = models.CharField(
        max_length=500, verbose_name="متن گزینه",
        help_text="پشتیبانی از LaTeX بین $...$",
    )
    is_correct = models.BooleanField(default=False, verbose_name="پاسخ صحیح؟")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        verbose_name = "گزینه"
        verbose_name_plural = "گزینه‌ها"
        ordering = ["order", "id"]

    def __str__(self):
        mark = "✓" if self.is_correct else "✗"
        return f"{mark} {self.text[:40]}"


# =====================================================================
#  4) آزمون
# =====================================================================
class Quiz(models.Model):
    """
    یک آزمون که مجموعه‌ای از سوالات بانک رو کنار هم می‌چینه.
    می‌تونه به یک دوره یا جلسه وصل باشه (اختیاری).
    """

    title = models.CharField(max_length=200, verbose_name="عنوان آزمون")
    slug = models.SlugField(max_length=220, unique=True, blank=True, verbose_name="slug")
    description = models.TextField(blank=True, verbose_name="توضیحات")

    # اتصال اختیاری به دوره / جلسه (با string reference تا وابستگی حلقوی پیش نیاد)
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="quizzes",
        blank=True,
        null=True,
        verbose_name="دوره",
    )
    lesson = models.ForeignKey(
        "courses.Lesson",
        on_delete=models.SET_NULL,
        related_name="quizzes",
        blank=True,
        null=True,
        verbose_name="جلسه",
    )

    # ارتباط چندبه‌چند با سوالات از طریق جدول واسط QuizQuestion
    questions = models.ManyToManyField(
        Question,
        through="QuizQuestion",
        related_name="quizzes",
        verbose_name="سوالات",
    )

    time_limit_minutes = models.PositiveSmallIntegerField(
        default=0, verbose_name="مدت زمان (دقیقه)",
        help_text="0 یعنی بدون محدودیت زمانی",
    )
    pass_mark = models.PositiveSmallIntegerField(
        default=50, verbose_name="حد نصاب قبولی (درصد)"
    )
    max_attempts = models.PositiveSmallIntegerField(
        default=0, verbose_name="حداکثر دفعات مجاز",
        help_text="0 یعنی نامحدود",
    )
    shuffle_questions = models.BooleanField(
        default=False, verbose_name="ترتیب تصادفی سوالات"
    )
    show_solution = models.BooleanField(
        default=True, verbose_name="نمایش راه‌حل بعد از آزمون"
    )
    is_published = models.BooleanField(default=False, verbose_name="منتشر شده")

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quizzes_created",
        verbose_name="سازنده",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "آزمون"
        verbose_name_plural = "آزمون‌ها"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("quiz:quiz_detail", kwargs={"slug": self.slug})

    def get_questions(self):
        """سوالات به ترتیب تعریف‌شده در QuizQuestion."""
        qs = self.quiz_questions.select_related("question").prefetch_related(
            "question__choices"
        )
        if self.shuffle_questions:
            qs = qs.order_by("?")
        return [qq.question for qq in qs]

    @property
    def total_points(self):
        """مجموع بارم همه سوالات آزمون."""
        agg = self.questions.aggregate(total=models.Sum("points"))
        return agg["total"] or 0

    @property
    def question_count(self):
        return self.questions.count()


class QuizQuestion(models.Model):
    """
    جدول واسط بین Quiz و Question.
    چرا جدول واسط سفارشی؟ تا بتونیم ترتیب سوالات رو نگه داریم.
    """

    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name="quiz_questions"
    )
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="quiz_links"
    )
    order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        verbose_name = "سوال آزمون"
        verbose_name_plural = "سوالات آزمون"
        ordering = ["order", "id"]
        unique_together = ["quiz", "question"]  # یک سوال دوبار در یک آزمون نیاد

    def __str__(self):
        return f"{self.quiz.title} → سوال {self.order}"


# =====================================================================
#  5) تلاش دانش‌آموز + پاسخ‌ها
# =====================================================================
class QuizAttempt(models.Model):
    """یک بار شرکت دانش‌آموز در یک آزمون."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    STATUS_CHOICES = (
        (IN_PROGRESS, "در حال انجام"),
        (COMPLETED, "تکمیل شده"),
    )

    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name="attempts", verbose_name="آزمون"
    )
    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="quiz_attempts", verbose_name="دانش‌آموز"
    )
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default=IN_PROGRESS, verbose_name="وضعیت"
    )
    score = models.FloatField(default=0, verbose_name="نمره کسب‌شده")
    max_score = models.FloatField(default=0, verbose_name="نمره کل")
    percentage = models.FloatField(default=0, verbose_name="درصد")
    is_passed = models.BooleanField(default=False, verbose_name="قبول؟")

    started_at = models.DateTimeField(auto_now_add=True, verbose_name="شروع")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="پایان")

    class Meta:
        verbose_name = "تلاش آزمون"
        verbose_name_plural = "تلاش‌های آزمون"
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["student", "quiz"])]

    def __str__(self):
        return f"{self.student} → {self.quiz.title} ({self.percentage}%)"

    def calculate_score(self):
        """
        جمع نمره همه پاسخ‌ها و محاسبه درصد و قبولی.
        این قلب تصحیح خودکاره.
        """
        answers = self.answers.all()
        self.score = sum(a.points_earned for a in answers)
        self.max_score = self.quiz.total_points or sum(
            a.question.points for a in answers
        )
        self.percentage = (
            round(self.score / self.max_score * 100, 2) if self.max_score else 0
        )
        self.is_passed = self.percentage >= self.quiz.pass_mark
        self.status = self.COMPLETED
        self.completed_at = timezone.now()
        self.save()
        return self.percentage


class AttemptAnswer(models.Model):
    """پاسخ دانش‌آموز به یک سوال در یک تلاش."""

    attempt = models.ForeignKey(
        QuizAttempt, on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="attempt_answers"
    )
    # برای سوالات گزینه‌محور
    selected_choices = models.ManyToManyField(
        Choice, blank=True, related_name="selected_in"
    )
    # برای سوالات عددی / کوتاه
    answer_text = models.CharField(max_length=255, blank=True, verbose_name="پاسخ متنی")

    is_correct = models.BooleanField(default=False, verbose_name="درست؟")
    points_earned = models.FloatField(default=0, verbose_name="نمره کسب‌شده")

    class Meta:
        verbose_name = "پاسخ"
        verbose_name_plural = "پاسخ‌ها"
        unique_together = ["attempt", "question"]

    def __str__(self):
        return f"{self.attempt.student} → سوال {self.question_id}"

    def grade(self):
        """
        تصحیح خودکار یک پاسخ.
        توجه: برای سوالات گزینه‌محور، اول باید selected_choices ست شده باشه
        (چون ManyToMany از دیتابیس خونده می‌شه).
        """
        q = self.question

        if q.is_choice_based:
            correct_ids = set(
                q.choices.filter(is_correct=True).values_list("id", flat=True)
            )
            selected_ids = set(self.selected_choices.values_list("id", flat=True))
            # جواب وقتی درسته که دقیقاً برابر مجموعه صحیح باشه
            self.is_correct = bool(correct_ids) and selected_ids == correct_ids

        elif q.question_type == Question.NUMERIC:
            try:
                val = float(self.answer_text)
                self.is_correct = (
                    q.correct_numeric is not None
                    and abs(val - q.correct_numeric) <= q.numeric_tolerance
                )
            except (TypeError, ValueError):
                self.is_correct = False

        elif q.question_type == Question.SHORT:
            self.is_correct = (
                self.answer_text.strip().lower() == q.correct_text.strip().lower()
                and q.correct_text != ""
            )

        self.points_earned = q.points if self.is_correct else 0
        self.save(update_fields=["is_correct", "points_earned"])
        return self.is_correct
