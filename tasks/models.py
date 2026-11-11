from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from projects.models import ProjectMembership


class Task(models.Model):
    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        REVIEW = "review", "Review"
        COMPLETED = "completed", "Completed"

    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="tasks"
    )
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_tasks"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TODO
    )
    deadline = models.DateField()
    position = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("position", "created_at", "pk")
        indexes = [
            models.Index(
                fields=("project", "status", "position"), name="task_board_position_idx"
            ),
            models.Index(
                fields=("assigned_to", "deadline"), name="task_assignee_due_idx"
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(priority__in=("low", "medium", "high", "critical")),
                name="task_priority_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=("todo", "in_progress", "review", "completed")
                ),
                name="task_status_valid",
            ),
        ]

    def clean(self):
        super().clean()
        self.title = self.title.strip()
        if not self.title:
            raise ValidationError({"title": "A task title is required."})
        if (
            self.assigned_to_id
            and not ProjectMembership.objects.filter(
                project_id=self.project_id,
                user_id=self.assigned_to_id,
                user__is_active=True,
            ).exists()
        ):
            raise ValidationError(
                {"assigned_to": "Choose an active member of this project."}
            )

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if update_fields is None or "status" in update_fields:
            self.completed_at = (
                (self.completed_at or timezone.now())
                if self.status == self.Status.COMPLETED
                else None
            )
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"completed_at"}
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title
