from functools import partial

from django.db import transaction

from .models import Notification
from .realtime import _publish


def visible_notifications(user):
    return Notification.objects.filter(recipient=user, project__memberships__user=user)


def notification_context(user):
    items = visible_notifications(user)
    return {
        "notification_unread_count": items.filter(read_at__isnull=True).count(),
        "notification_items": list(items.select_related("project", "task")[:10]),
    }


def notifications_changed(user_id):
    transaction.on_commit(
        partial(_publish, (user_id,), "notifications.changed"), robust=True
    )


def task_assigned(task, actor, previous_assignee_id=None):
    if not task.assigned_to_id or task.assigned_to_id in (
        actor.pk,
        previous_assignee_id,
    ):
        return
    name = actor.get_full_name() or actor.email
    Notification.objects.create(
        recipient_id=task.assigned_to_id,
        actor=actor,
        project_id=task.project_id,
        task=task,
        kind=Notification.Kind.TASK_ASSIGNED,
        message=f"{name} assigned you “{task.title}”.",
    )
    notifications_changed(task.assigned_to_id)


def project_member_added(membership, actor):
    if membership.user_id == actor.pk:
        return
    name = actor.get_full_name() or actor.email
    Notification.objects.create(
        recipient_id=membership.user_id,
        actor=actor,
        project_id=membership.project_id,
        kind=Notification.Kind.PROJECT_ADDED,
        message=f"{name} added you to “{membership.project.title}”.",
    )
    notifications_changed(membership.user_id)
