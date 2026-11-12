import asyncio
import logging
from functools import partial

from asgiref.sync import async_to_sync
from channels.exceptions import ChannelFull
from channels.layers import get_channel_layer
from django.contrib.sessions.models import Session
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver
from redis.exceptions import RedisError

from projects.models import Project, ProjectMembership
from tasks.models import Task

logger = logging.getLogger(__name__)


async def _broadcast(user_ids, event_type):
    async with asyncio.timeout(2):
        layer = get_channel_layer()
        for user_id in user_ids:
            await layer.group_send(f"dashboard.user.{user_id}", {"type": event_type})


def _publish(user_ids, event_type="dashboard.changed"):
    try:
        async_to_sync(_broadcast)(user_ids, event_type)
    except (RedisError, OSError, ChannelFull):
        logger.warning("Dashboard notification unavailable.")


def notify_project(project_id, using, extra_users=()):
    user_ids = set(
        ProjectMembership.objects.using(using)
        .filter(project_id=project_id)
        .values_list("user_id", flat=True)
    ) | set(extra_users)
    if user_ids:
        transaction.on_commit(
            partial(_publish, tuple(user_ids)), using=using, robust=True
        )


def _deleting_project(origin):
    return isinstance(origin, Project) or getattr(origin, "model", None) is Project


@receiver(post_save, sender=Task)
def task_saved(sender, instance, using, raw=False, **kwargs):
    if not raw:
        notify_project(instance.project_id, using)


@receiver(post_delete, sender=Task)
def task_deleted(sender, instance, using, origin, **kwargs):
    if not _deleting_project(origin):
        notify_project(instance.project_id, using)


@receiver(post_save, sender=Project)
def project_saved(sender, instance, using, raw=False, **kwargs):
    if not raw:
        notify_project(instance.pk, using, (instance.owner_id,))


@receiver(pre_delete, sender=Project)
def project_deleting(sender, instance, using, **kwargs):
    # Capture members before the project's memberships are deleted.
    notify_project(instance.pk, using)


@receiver(post_save, sender=ProjectMembership)
def membership_saved(sender, instance, using, raw=False, **kwargs):
    if not raw:
        notify_project(instance.project_id, using, (instance.user_id,))


@receiver(post_delete, sender=ProjectMembership)
def membership_deleted(sender, instance, using, origin, **kwargs):
    if not _deleting_project(origin):
        notify_project(instance.project_id, using, (instance.user_id,))


@receiver(post_delete, sender=Session)
def session_deleted(sender, instance, using, **kwargs):
    user_id = instance.get_decoded().get("_auth_user_id")
    if user_id:
        transaction.on_commit(partial(_publish, (user_id,)), using=using, robust=True)
