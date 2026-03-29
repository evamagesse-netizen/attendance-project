import json
import re
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods

from .models import Attendance, Employee

BARCODE_MAX_LEN = 128
BARCODE_PATTERN = re.compile(r"^[A-Za-z0-9\-_.]+$")
SCAN_MODES = frozenset({"check-in", "check-out"})


def _parse_json_body(request):
    if not request.body:
        return None, "Empty request body."
    try:
        return json.loads(request.body.decode("utf-8")), None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, "Invalid JSON."


def _validate_mode(raw):
    if raw is None:
        return None, 'Scan mode is required: use "check-in" or "check-out".'
    mode = str(raw).strip()
    if mode not in SCAN_MODES:
        return None, 'Scan mode must be "check-in" or "check-out".'
    return mode, None


def _validate_barcode(raw):
    if raw is None:
        return None, "Barcode is required."
    barcode = str(raw).strip()
    if not barcode:
        return None, "Barcode cannot be empty."
    if len(barcode) > BARCODE_MAX_LEN:
        return None, f"Barcode must be at most {BARCODE_MAX_LEN} characters."
    if not BARCODE_PATTERN.match(barcode):
        return None, "Barcode may only contain letters, numbers, hyphen, underscore, and period."
    return barcode, None


@ensure_csrf_cookie
@require_GET
def scanner_page(request):
    return render(request, "employees/scanner.html")


@require_GET
def dashboard(request):
    raw_date = request.GET.get("date")
    if raw_date:
        try:
            filter_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            filter_date = timezone.localdate()
    else:
        filter_date = timezone.localdate()

    records = (
        Attendance.objects.filter(date=filter_date)
        .select_related("employee")
        .order_by("check_in")
    )

    total_employees = Employee.objects.count()
    attendance_qs = Attendance.objects.filter(date=filter_date)
    checked_in_count = attendance_qs.count()
    checked_out_count = attendance_qs.filter(check_out__isnull=False).count()

    return render(
        request,
        "employees/dashboard.html",
        {
            "filter_date": filter_date,
            "records": records,
            "total_employees": total_employees,
            "checked_in_count": checked_in_count,
            "checked_out_count": checked_out_count,
            "time_zone": settings.TIME_ZONE,
        },
    )


@require_http_methods(["POST"])
def scan_barcode(request):
    data, err = _parse_json_body(request)
    if err:
        return JsonResponse(
            {"status": "error", "action": None, "employee_name": None, "message": err},
            status=400,
        )

    barcode, verr = _validate_barcode(data.get("barcode") if isinstance(data, dict) else None)
    if verr:
        return JsonResponse(
            {"status": "error", "action": None, "employee_name": None, "message": verr},
            status=400,
        )

    mode, merr = _validate_mode(data.get("mode") if isinstance(data, dict) else None)
    if merr:
        return JsonResponse(
            {"status": "error", "action": None, "employee_name": None, "message": merr},
            status=400,
        )

    try:
        employee = Employee.objects.get(barcode=barcode)
    except Employee.DoesNotExist:
        return JsonResponse(
            {
                "status": "error",
                "action": None,
                "employee_name": None,
                "message": "No employee found for this barcode.",
            },
            status=404,
        )

    today = timezone.localdate()
    now = timezone.now()

    if mode == "check-in":
        try:
            attendance = Attendance.objects.get(employee=employee, date=today)
        except Attendance.DoesNotExist:
            Attendance.objects.create(employee=employee, date=today, check_in=now)
            return JsonResponse(
                {
                    "status": "success",
                    "action": "check-in",
                    "employee_name": employee.name,
                    "message": f"Welcome, {employee.name}.",
                }
            )

        if attendance.check_out is None:
            return JsonResponse(
                {
                    "status": "error",
                    "action": None,
                    "employee_name": employee.name,
                    "message": "Already checked in. Select Check out to scan departure.",
                },
                status=409,
            )
        return JsonResponse(
            {
                "status": "error",
                "action": None,
                "employee_name": employee.name,
                "message": "Attendance for today is already complete. Check in is not allowed.",
            },
            status=409,
        )

    # mode == "check-out"
    try:
        attendance = Attendance.objects.get(employee=employee, date=today)
    except Attendance.DoesNotExist:
        return JsonResponse(
            {
                "status": "error",
                "action": None,
                "employee_name": employee.name,
                "message": "No check-in for today. Select Check in first.",
            },
            status=400,
        )

    if attendance.check_out is not None:
        return JsonResponse(
            {
                "status": "error",
                "action": None,
                "employee_name": employee.name,
                "message": "Already checked out for today.",
            },
            status=409,
        )

    attendance.check_out = now
    attendance.save(update_fields=["check_out"])

    return JsonResponse(
        {
            "status": "success",
            "action": "check-out",
            "employee_name": employee.name,
            "message": f"Goodbye, {employee.name}.",
        }
    )
