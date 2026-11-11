from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def home(request):
    return render(request, "core/home.html")


def database_connected():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone() == (1,)
    except DatabaseError:
        return False


@require_GET
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
def connection_status(request):
    return render(
        request,
        "core/partials/connection_status.html",
        {"connected": database_connected()},
    )
