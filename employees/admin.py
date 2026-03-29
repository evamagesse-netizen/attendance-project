from django.contrib import admin
from django.utils.html import format_html

from .models import Attendance, Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("name", "employee_id", "barcode", "qr_thumb")
    search_fields = ("name", "employee_id", "barcode")
    fieldsets = (
        (None, {"fields": ("name", "employee_id")}),
        (
            "Barcode & QR (for ID cards)",
            {
                "description": "The QR image encodes the barcode value used by the attendance scanner.",
                "fields": ("barcode", "barcode_image", "qr_preview", "download_link"),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ("barcode_image", "qr_preview", "download_link")
        return ("barcode", "barcode_image", "qr_preview", "download_link")

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return (
                (None, {"fields": ("name", "employee_id")}),
                (
                    "Barcode (optional)",
                    {
                        "description": "Leave blank to auto-generate a unique barcode and QR image when you save.",
                        "fields": ("barcode",),
                    },
                ),
            )
        return super().get_fieldsets(request, obj)

    @admin.display(description="QR")
    def qr_thumb(self, obj):
        if obj.barcode_image:
            return format_html(
                '<img src="{}" alt="" style="height:36px;width:auto;border-radius:4px;" />',
                obj.barcode_image.url,
            )
        return "—"

    @admin.display(description="Preview")
    def qr_preview(self, obj):
        if not obj.barcode_image:
            return "—"
        return format_html(
            '<img src="{}" alt="QR" style="max-width:220px;height:auto;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.12);" />',
            obj.barcode_image.url,
        )

    @admin.display(description="Download")
    def download_link(self, obj):
        if not obj.barcode_image:
            return "—"
        name = f"{obj.employee_id}_barcode_qr.png"
        return format_html(
            '<a href="{}" download="{}">Download PNG</a>',
            obj.barcode_image.url,
            name,
        )


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "check_in", "check_out")
    list_filter = ("date",)
    search_fields = ("employee__name", "employee__employee_id")
    date_hierarchy = "date"
