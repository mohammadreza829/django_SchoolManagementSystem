"""تست‌های فرایند پرداخت زرین‌پال (با mock کردن درگاه)."""

from decimal import Decimal
from unittest import mock

from django.test import TestCase

from accounts.models import User
from courses.models import Course
from courses.policies import has_course_access
from Enrollment.models import Enrollment

from .models import Payment
from .services import verify_payment, start_payment


class PaymentFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student1",
            email="s1@example.com",
            password="pass12345",
            national_code="1234567890",
        )
        self.course = Course.objects.create(
            title="دورهٔ تست پرداخت",
            description="...",
            short_description="...",
            status="published",
            price=100000,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.user,
            course=self.course,
            status="active",
            payment_status="pending",
            price_paid=0,
        )

    def test_start_payment_creates_record_and_returns_gateway_url(self):
        with mock.patch(
            "payments.services.gateways.request_payment",
            return_value=(
                "A0000000000000000000000000000000abcd",
                "https://sandbox.zarinpal.com/pg/StartPay/A0000000000000000000000000000000abcd",
            ),
        ) as req:
            url = start_payment(
                user=self.user,
                course=self.course,
                callback_url="http://testserver/payments/callback/",
            )
        self.assertIn("StartPay", url)
        payment = Payment.objects.get()
        self.assertEqual(payment.status, Payment.STATUS_INITIATED)
        self.assertEqual(payment.amount, Decimal("100000"))
        self.assertTrue(payment.authority)
        req.assert_called_once()

    def test_verify_payment_success_grants_access(self):
        payment = Payment.objects.create(
            user=self.user, course=self.course, enrollment=self.enrollment,
            amount=self.course.final_price,
            authority="A0000000000000000000000000000000okk1",
            status=Payment.STATUS_INITIATED,
        )
        with mock.patch(
            "payments.services.gateways.verify_payment",
            return_value=("123456789", False),
        ):
            result, ok = verify_payment(authority=payment.authority, gateway_status="OK")
        self.assertTrue(ok)
        result.refresh_from_db()
        self.assertEqual(result.status, Payment.STATUS_PAID)
        self.assertEqual(result.ref_id, "123456789")
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.payment_status, "paid")
        self.assertTrue(has_course_access(self.user, self.course))

    def test_verify_payment_cancelled_marks_failed(self):
        payment = Payment.objects.create(
            user=self.user, course=self.course, enrollment=self.enrollment,
            amount=self.course.final_price,
            authority="A0000000000000000000000000000000nok1",
            status=Payment.STATUS_INITIATED,
        )
        result, ok = verify_payment(authority=payment.authority, gateway_status="NOK")
        self.assertFalse(ok)
        result.refresh_from_db()
        self.assertEqual(result.status, Payment.STATUS_FAILED)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.payment_status, "failed")
        self.assertFalse(has_course_access(self.user, self.course))

    def test_verify_payment_is_idempotent(self):
        payment = Payment.objects.create(
            user=self.user, course=self.course, enrollment=self.enrollment,
            amount=self.course.final_price,
            authority="A0000000000000000000000000000000idem",
            status=Payment.STATUS_PAID, ref_id="555",
        )
        with mock.patch("payments.services.gateways.verify_payment") as verify:
            result, ok = verify_payment(authority=payment.authority, gateway_status="OK")
        self.assertTrue(ok)
        verify.assert_not_called()
