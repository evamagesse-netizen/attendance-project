from django.urls import path

from . import views

urlpatterns = [
    path("", views.scanner_page, name="scanner"),
    path("scan-barcode/", views.scan_barcode, name="scan_barcode"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("admin/time-rules/", views.admin_time_rules, name="admin_time_rules"),
]
