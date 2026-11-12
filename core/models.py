from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        TASK_ASSIGNED = "task_assigned", "Task assigned"
        PROJECT_ADDED = "project_added", "Added to project"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_notifications",
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="notifications"
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    message = models.CharField(max_length=600)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        indexes = (
            models.Index(
                fields=("recipient", "read_at", "-created_at"),
                name="notif_recipient_read_idx",
            ),
        )
