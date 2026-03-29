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
        r = self._csrf_post('{"barcode": "BAR001"}')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"], "check-in")

        r2 = self._csrf_post('{"barcode": "BAR001"}')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["action"], "check-out")

        r3 = self._csrf_post('{"barcode": "BAR001"}')
        self.assertEqual(r3.status_code, 409)

    def test_unknown_barcode(self):
        r = self._csrf_post('{"barcode": "nope"}')
        self.assertEqual(r.status_code, 404)
