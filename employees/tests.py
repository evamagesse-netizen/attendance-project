import tempfile

from django.test import Client, TestCase
from django.utils import timezone

from .models import Attendance, Employee


class ScanBarcodeTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.emp = Employee.objects.create(
            name="Jane Doe",
            employee_id="E1",
            barcode="BAR001",
        )

    def _csrf_post(self, payload):
        url = "/scan-barcode/"
        self.client.get("/")
        return self.client.post(
            url,
            data=payload,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.client.cookies.get("csrftoken").value,
        )

    def test_check_in_then_out(self):
        r = self._csrf_post('{"barcode": "BAR001", "mode": "check-in"}')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"], "check-in")

        r2 = self._csrf_post('{"barcode": "BAR001", "mode": "check-out"}')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["action"], "check-out")

        r3 = self._csrf_post('{"barcode": "BAR001", "mode": "check-out"}')
        self.assertEqual(r3.status_code, 409)

    def test_check_out_without_check_in(self):
        r = self._csrf_post('{"barcode": "BAR001", "mode": "check-out"}')
        self.assertEqual(r.status_code, 400)
        self.assertIn("check-in", r.json()["message"].lower())

    def test_double_check_in_blocked(self):
        self._csrf_post('{"barcode": "BAR001", "mode": "check-in"}')
        r = self._csrf_post('{"barcode": "BAR001", "mode": "check-in"}')
        self.assertEqual(r.status_code, 409)

    def test_unknown_barcode(self):
        r = self._csrf_post('{"barcode": "nope", "mode": "check-in"}')
        self.assertEqual(r.status_code, 404)

    def test_mode_required(self):
        r = self._csrf_post('{"barcode": "BAR001"}')
        self.assertEqual(r.status_code, 400)


class EmployeeAutoBarcodeTests(TestCase):
    def test_auto_barcode_and_qr_image_on_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.settings(MEDIA_ROOT=tmp):
                emp = Employee.objects.create(name="Auto User", employee_id="AUTO-1")
            emp.refresh_from_db()
        self.assertTrue(emp.barcode)
        self.assertGreaterEqual(len(emp.barcode), 8)
        self.assertTrue(emp.barcode_image)
        self.assertIn(".png", emp.barcode_image.name)

    def test_explicit_barcode_still_gets_qr(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.settings(MEDIA_ROOT=tmp):
                emp = Employee.objects.create(
                    name="Explicit",
                    employee_id="AUTO-2",
                    barcode="CUSTOM123",
                )
            emp.refresh_from_db()
        self.assertEqual(emp.barcode, "CUSTOM123")
        self.assertTrue(emp.barcode_image)
