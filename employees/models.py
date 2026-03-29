from datetime import time as dt_time

from django.db import models
from django.utils import timezone


class Employee(models.Model):
    name = models.CharField(max_length=200)
    employee_id = models.CharField(max_length=64, unique=True, db_index=True)
    barcode = models.CharField(max_length=128, unique=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.employee_id})"


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
