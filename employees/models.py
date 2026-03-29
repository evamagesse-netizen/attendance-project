from datetime import time as dt_time

from django.db import models
from django.utils import timezone


def _employee_barcode_upload(instance, filename):
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in instance.employee_id)[:48]
    return f"employee_barcodes/{safe}_{instance.pk}_qr.png"


class Employee(models.Model):
    name = models.CharField(max_length=200)
    employee_id = models.CharField(max_length=64, unique=True, db_index=True)
    barcode = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        blank=True,
        help_text="Leave empty when adding an employee; a unique code is generated automatically.",
    )
    barcode_image = models.FileField(
        upload_to=_employee_barcode_upload,
        blank=True,
        max_length=255,
        help_text="QR image encoding the barcode (for ID cards and scanning).",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.employee_id})"

    def save(self, *args, **kwargs):
        from .barcode_utils import generate_unique_barcode, qr_png_content_file

        old_barcode = None
        if self.pk:
            prev = Employee.objects.filter(pk=self.pk).only("barcode", "barcode_image").first()
            if prev:
                old_barcode = prev.barcode

        if self.barcode is not None:
            self.barcode = str(self.barcode).strip()

        if not self.barcode:
            self.barcode = generate_unique_barcode()

        super().save(*args, **kwargs)

        need_qr = (old_barcode != self.barcode) or not self.barcode_image
        if need_qr:
            name = f"emp_{self.pk}_qr.png"
            content = qr_png_content_file(self.barcode, name)
            self.barcode_image.save(name, content, save=False)
            super().save(update_fields=["barcode_image"])


class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField(db_index=True)
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date", "-check_in"]
        constraints = [
            models.UniqueConstraint(fields=["employee", "date"], name="unique_employee_date"),
        ]

    def __str__(self):
        return f"{self.employee.name} — {self.date}"

    @property
    def is_late_check_in(self):
        """Check-in after 9:00 AM in the active timezone."""
        local = timezone.localtime(self.check_in)
        return local.time() > dt_time(9, 0)
