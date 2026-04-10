from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from employees import views as employee_views

urlpatterns = [
    path("admin/dashboard/login/", employee_views.admin_dashboard_login, name="admin_dashboard_login"),
    path("admin/dashboard/logout/", employee_views.admin_dashboard_logout, name="admin_dashboard_logout"),
    path("admin/dashboard/", employee_views.admin_dashboard, name="admin_dashboard"),
    path("admin/dashboard/time-rules/", employee_views.admin_time_rules_page, name="admin_time_rules_page"),
    path(
        "admin/dashboard/leave-permissions/",
        employee_views.admin_leave_permissions_page,
        name="admin_leave_permissions_page",
    ),
    path("admin/dashboard/employees/", employee_views.admin_employees_page, name="admin_employees_page"),
    path("admin/dashboard/admin-users/", employee_views.admin_users_page, name="admin_users_page"),
    path("admin/", admin.site.urls),
    path("", include("employees.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
