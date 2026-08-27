"""رندر صفحات عمومی تا خطای قالب قبل از مرج گرفته شود."""

from django.test import TestCase
from django.urls import reverse

from .models import Category
from .tests import create_course, create_user


class PublicPagesRenderTests(TestCase):
    """لندینگ، لیست، جست‌وجو و دسته باید با کارت دوره واقعاً رندر شوند."""

    @classmethod
    def setUpTestData(cls):
        cls.teacher = create_user(
            "teacher_public",
            role="teacher",
            first_name="استاد",
            last_name="نمونه",
        )
        cls.category = Category.objects.create(
            name="برنامه‌نویسی",
            slug="programming",
            icon="code",
        )
        cls.course = create_course(
            "دورهٔ جنگو ویژه",
            price=250000,
            discount_percent=20,
            category=cls.category,
            duration_hours=24,
            total_lessons=18,
            enroll_count=42,
            rating_avg="4.50",
            rating_count=12,
        )
        cls.course.teachers.add(cls.teacher)

    def test_home_page_renders_with_course_card(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "دورهٔ جنگو ویژه")
        self.assertContains(response, "هر چیزی که")

    def test_course_list_page_renders(self):
        response = self.client.get(reverse("courses:course_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "دورهٔ جنگو ویژه")

    def test_category_detail_page_renders(self):
        response = self.client.get(
            reverse("courses:category_detail", kwargs={"slug": "programming"})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "برنامه‌نویسی")
        self.assertContains(response, "دورهٔ جنگو ویژه")

    def test_search_results_render_course_card(self):
        response = self.client.get(reverse("courses:search"), {"q": "جنگو"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "دورهٔ جنگو ویژه")
