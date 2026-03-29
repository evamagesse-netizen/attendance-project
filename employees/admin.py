from django.contrib import admin

from .models import Attendance, Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("name", "employee_id", "barcode")
    search_fields = ("name", "employee_id", "barcode")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "check_in", "check_out")
    list_filter = ("date",)
    search_fields = ("employee__name", "employee__employee_id")
    date_hierarchy = "date"
