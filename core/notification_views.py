from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .notifications import (
    notification_context,
    notifications_changed,
    visible_notifications,
)


@require_GET
@never_cache
def notification_list(request):
    return render(
        request, "core/partials/notifications.html", notification_context(request.user)
    )


@require_POST
@never_cache
@transaction.atomic
def notification_open(request, pk):
    item = get_object_or_404(
        visible_notifications(request.user).select_for_update(of=("self",)), pk=pk
    )
    if item.read_at is None:
        item.read_at = timezone.now()
        item.save(update_fields=["read_at"])
        notifications_changed(request.user.pk)
    if item.task_id:
        return redirect("tasks:detail", project_pk=item.project_id, pk=item.task_id)
    return redirect("projects:detail", pk=item.project_id)


@require_POST
@never_cache
@transaction.atomic
def notification_read_all(request):
    changed = (
        visible_notifications(request.user)
        .filter(read_at__isnull=True)
        .update(read_at=timezone.now())
    )
    if changed:
        notifications_changed(request.user.pk)
    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "core/partials/notifications.html",
            notification_context(request.user),
        )
    return redirect("core:dashboard")
