import json
import re
from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods

from .models import Attendance, Employee, EmployeeSchedule, LeavePermission

BARCODE_MAX_LEN = 128
BARCODE_PATTERN = re.compile(r"^[A-Za-z0-9\-_.]+$")
SCAN_MODES = frozenset({"check-in", "check-out"})
User = get_user_model()


def _is_staff_user(user):
    return user.is_authenticated and user.is_staff


def _is_superuser(user):
    return user.is_authenticated and user.is_superuser


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

    local_now = timezone.localtime(now)
    schedule = getattr(employee, "schedule", None)
    if schedule and local_now.time() < schedule.leave_time:
        permission = (
            LeavePermission.objects.filter(
                employee=employee,
                date=today,
                used_at__isnull=True,
            )
            .order_by("created_at")
            .first()
        )
        if permission is None:
            return JsonResponse(
                {
                    "status": "error",
                    "action": None,
                    "employee_name": employee.name,
                    "message": (
                        f"Check-out is allowed after {schedule.leave_time.strftime('%H:%M')}. "
                        "Please request admin permission for early leave."
                    ),
                },
                status=403,
            )
        permission.used_at = now
        permission.save(update_fields=["used_at"])

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


@login_required
@user_passes_test(_is_staff_user)
@require_http_methods(["GET", "POST"])
def admin_dashboard(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "set_schedule":
            employee_id = request.POST.get("employee_id")
            report_time = request.POST.get("report_time")
            leave_time = request.POST.get("leave_time")

            try:
                employee = Employee.objects.get(pk=employee_id)
            except (Employee.DoesNotExist, ValueError, TypeError):
                messages.error(request, "Invalid employee selected.")
                return redirect("admin_dashboard")

            if not report_time or not leave_time:
                messages.error(request, "Both report time and leave time are required.")
                return redirect("admin_dashboard")

            try:
                parsed_report_time = datetime.strptime(report_time, "%H:%M").time()
                parsed_leave_time = datetime.strptime(leave_time, "%H:%M").time()
            except ValueError:
                messages.error(request, "Invalid time format.")
                return redirect("admin_dashboard")

            if parsed_leave_time <= parsed_report_time:
                messages.error(request, "Leave time must be after report time.")
                return redirect("admin_dashboard")

            EmployeeSchedule.objects.update_or_create(
                employee=employee,
                defaults={
                    "report_time": parsed_report_time,
                    "leave_time": parsed_leave_time,
                },
            )
            messages.success(request, f"Updated time rules for {employee.name}.")
            return redirect("admin_dashboard")

        if action == "grant_permission":
            employee_id = request.POST.get("employee_id")
            reason = (request.POST.get("reason") or "").strip()
            date_raw = request.POST.get("date")

            try:
                employee = Employee.objects.get(pk=employee_id)
            except (Employee.DoesNotExist, ValueError, TypeError):
                messages.error(request, "Invalid employee selected.")
                return redirect("admin_dashboard")

            if not date_raw:
                permission_date = timezone.localdate()
            else:
                try:
                    permission_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
                except ValueError:
                    messages.error(request, "Invalid permission date.")
                    return redirect("admin_dashboard")

            permission = LeavePermission.objects.filter(
                employee=employee,
                date=permission_date,
                used_at__isnull=True,
            ).first()
            if permission:
                permission.approved_by = request.user.get_username() or "admin"
                permission.reason = reason
                permission.save(update_fields=["approved_by", "reason"])
            else:
                LeavePermission.objects.create(
                    employee=employee,
                    date=permission_date,
                    approved_by=request.user.get_username() or "admin",
                    reason=reason,
                )
            messages.success(
                request,
                f"Permission granted for {employee.name} on {permission_date}.",
            )
            return redirect("admin_dashboard")

        if action == "create_admin":
            if not request.user.is_superuser:
                messages.error(request, "Only superusers can create admin users.")
                return redirect("admin_dashboard")
            username = (request.POST.get("username") or "").strip()
            password = request.POST.get("password") or ""
            is_superuser = request.POST.get("is_superuser") == "on"
            if not username or not password:
                messages.error(request, "Username and password are required.")
                return redirect("admin_dashboard")
            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists.")
                return redirect("admin_dashboard")

            User.objects.create_user(
                username=username,
                password=password,
                is_staff=True,
                is_superuser=is_superuser,
            )
            messages.success(request, f"Admin user '{username}' created.")
            return redirect("admin_dashboard")

        if action == "update_admin":
            if not request.user.is_superuser:
                messages.error(request, "Only superusers can update admin users.")
                return redirect("admin_dashboard")
            user_id = request.POST.get("user_id")
            new_password = request.POST.get("new_password") or ""
            is_staff = request.POST.get("is_staff") == "on"
            is_superuser = request.POST.get("is_superuser") == "on"
            is_active = request.POST.get("is_active") == "on"
            try:
                admin_user = User.objects.get(pk=user_id)
            except (User.DoesNotExist, ValueError, TypeError):
                messages.error(request, "Invalid admin user selected.")
                return redirect("admin_dashboard")

            if admin_user == request.user and not is_staff:
                messages.error(request, "You cannot remove your own staff access.")
                return redirect("admin_dashboard")
            if admin_user == request.user and not is_active:
                messages.error(request, "You cannot deactivate your own account.")
                return redirect("admin_dashboard")

            admin_user.is_staff = is_staff
            admin_user.is_superuser = is_superuser
            admin_user.is_active = is_active
            if new_password:
                admin_user.set_password(new_password)
            admin_user.save()
            messages.success(request, f"Updated admin user '{admin_user.username}'.")
            return redirect("admin_dashboard")

        if action == "delete_admin":
            if not request.user.is_superuser:
                messages.error(request, "Only superusers can delete admin users.")
                return redirect("admin_dashboard")
            user_id = request.POST.get("user_id")
            try:
                admin_user = User.objects.get(pk=user_id)
            except (User.DoesNotExist, ValueError, TypeError):
                messages.error(request, "Invalid admin user selected.")
                return redirect("admin_dashboard")
            if admin_user == request.user:
                messages.error(request, "You cannot delete your own account.")
                return redirect("admin_dashboard")
            username = admin_user.username
            admin_user.delete()
            messages.success(request, f"Deleted admin user '{username}'.")
            return redirect("admin_dashboard")

        messages.error(request, "Unsupported action.")
        return redirect("admin_dashboard")

    employees = Employee.objects.all().select_related("schedule")
    today = timezone.localdate()
    active_permissions = (
        LeavePermission.objects.filter(date=today, used_at__isnull=True)
        .select_related("employee")
        .order_by("employee__name")
    )
    admin_users = User.objects.filter(is_staff=True).order_by("username")
    return render(
        request,
        "admin/dashboard.html",
        {
            "employees": employees,
            "active_permissions": active_permissions,
            "admin_users": admin_users,
            "today": today,
            "can_manage_admins": request.user.is_superuser,
        },
    )


@require_http_methods(["GET", "POST"])
def admin_dashboard_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("admin_dashboard")

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        user = authenticate(request, username=username, password=password)
        if user and user.is_staff and user.is_active:
            login(request, user)
            return redirect("admin_dashboard")
        messages.error(request, "Invalid admin credentials.")

    return render(request, "admin/login.html")


@login_required
@user_passes_test(_is_staff_user)
@require_http_methods(["POST"])
def admin_dashboard_logout(request):
    logout(request)
    return redirect("admin_dashboard_login")
