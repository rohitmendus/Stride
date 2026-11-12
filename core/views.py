from datetime import timedelta

from django.contrib.auth.decorators import login_not_required
from django.db import DatabaseError, connection
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.cache import patch_vary_headers
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from projects.views import project_list
from tasks.models import Task


@require_GET
@never_cache
def home(request):
    return project_list(request)


@require_GET
@never_cache
def dashboard(request):
    today = timezone.localdate()
    tasks = Task.objects.filter(project__memberships__user=request.user)
    summary = tasks.aggregate(
        total=Count("pk"),
        overdue=Count(
            "pk", filter=Q(deadline__lt=today) & ~Q(status=Task.Status.COMPLETED)
        ),
        **{
            status: Count("pk", filter=Q(status=status))
            for status, _ in Task.Status.choices
        },
    )
    summary["pending"] = summary["total"] - summary["completed"]
    unfinished = (
        tasks.exclude(status=Task.Status.COMPLETED)
        .select_related("project", "assigned_to")
        .order_by("deadline", "pk")
    )
    context = {
        "dashboard_workspace": True,
        "summary": summary,
        "metrics": [
            {"key": key, "label": label, "value": summary[key], "detail": detail}
            for key, label, detail in (
                ("total", "Total tasks", "Across your projects"),
                ("completed", "Completed", "Finished work"),
                ("pending", "Pending", "To do, in progress, review"),
                ("overdue", "Overdue", "Unfinished and past due"),
            )
        ],
        "chart": [
            {
                "status": status,
                "label": label,
                "count": summary[status],
                "percent": round(summary[status] * 100 / summary["total"], 2)
                if summary["total"]
                else 0,
            }
            for status, label in Task.Status.choices
        ],
        "overdue_tasks": list(unfinished.filter(deadline__lt=today)[:3]),
        "upcoming_tasks": list(
            unfinished.filter(
                deadline__gte=today, deadline__lte=today + timedelta(days=7)
            )[:3]
        ),
        "updated_at": timezone.now(),
    }
    partial = (
        request.headers.get("HX-Request") == "true"
        and request.headers.get("HX-Target") == "dashboard-content"
    )
    response = render(
        request,
        "core/partials/dashboard.html" if partial else "core/dashboard.html",
        context,
    )
    patch_vary_headers(response, ("HX-Request", "HX-Target"))
    return response


def database_connected():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone() == (1,)
    except DatabaseError:
        return False


@require_GET
@login_not_required
def health(request):
    connected = database_connected()
    return JsonResponse(
        {
            "status": "ok" if connected else "error",
            "database": "connected" if connected else "unavailable",
        },
        status=200 if connected else 503,
    )


@require_GET
@login_not_required
def connection_status(request):
    return render(
        request,
        "core/partials/connection_status.html",
        {"connected": database_connected()},
    )
