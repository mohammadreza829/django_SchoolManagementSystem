"""رندر صفحات عمومی تا خطای قالب قبل از مرج گرفته شود."""

from django.test import TestCase
from django.urls import reverse

from .models import Category
from .tests import TEST_PASSWORD, create_course, create_user


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

    def test_home_always_shows_classroom_mockup(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "چت کلاس")
        self.assertContains(response, "classroom")

    def test_anonymous_home_hides_quiz_nav(self):
        response = self.client.get(reverse("home"))
        quiz_url = reverse("quiz:quiz_list")

        self.assertNotContains(response, f'href="{quiz_url}"')

    def test_logged_in_home_shows_quiz_nav(self):
        student = create_user("nav_student")
        self.client.login(username=student.username, password=TEST_PASSWORD)
        response = self.client.get(reverse("home"))
        quiz_url = reverse("quiz:quiz_list")

        self.assertContains(response, f'href="{quiz_url}"')

    def test_anonymous_quiz_list_redirects_to_login(self):
        response = self.client.get(reverse("quiz:quiz_list"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

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
