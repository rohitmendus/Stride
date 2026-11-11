from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
from django.utils import timezone


class Project(models.Model):
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    deadline = models.DateField()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_projects",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="ProjectMembership", related_name="projects"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "pk")

    def clean(self):
        super().clean()
        self.title = self.title.strip()
        if not self.title:
            raise ValidationError({"title": "A project title is required."})
        if self.pk and not self._state.adding:
            owner_id = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("owner_id", flat=True)
                .first()
            )
            if owner_id is not None and owner_id != self.owner_id:
                raise ValidationError({"owner": "Project ownership cannot be changed."})

    def save(self, *args, **kwargs):
        creating = self._state.adding
        self.full_clean()
        with transaction.atomic():
            result = super().save(*args, **kwargs)
            if creating:
                ProjectMembership.objects.create(
                    project=self, user=self.owner, role=ProjectMembership.Role.ADMIN
                )
            return result

    def __str__(self):
        return self.title


class ProjectMembership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_memberships",
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("project", "user"), name="project_member_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=("admin", "member")),
                name="project_member_role_valid",
            ),
        ]

    def clean(self):
        super().clean()
        owner_id = (
            Project.objects.filter(pk=self.project_id)
            .values_list("owner_id", flat=True)
            .first()
        )
        if owner_id == self.user_id and self.role != self.Role.ADMIN:
            raise ValidationError({"role": "The project owner must remain an admin."})
        if (
            self._state.adding
            and self.user_id
            and not get_user_model()
            .objects.filter(pk=self.user_id, is_active=True)
            .exists()
        ):
            raise ValidationError({"user": "Only active users can join a project."})
        if self.pk and not self._state.adding:
            previous = (
                type(self)
                .objects.filter(pk=self.pk)
                .values("project_id", "user_id")
                .first()
            )
            if previous and (
                previous["project_id"] != self.project_id
                or previous["user_id"] != self.user_id
            ):
                raise ValidationError(
                    "Remove the membership and add a new one instead of changing its project or user."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} · {self.project} ({self.get_role_display()})"


@receiver(pre_delete, sender=ProjectMembership)
def protect_owner_membership(sender, instance, origin, **kwargs):
    deleting_project = (
        isinstance(origin, Project) or getattr(origin, "model", None) is Project
    )
    if not deleting_project and instance.user_id == instance.project.owner_id:
        raise ValidationError("The project owner cannot be removed.")


@receiver(post_delete, sender=ProjectMembership)
def unassign_removed_member(sender, instance, using, **kwargs):
    Task = apps.get_model("tasks", "Task")
    Task.objects.using(using).filter(
        project_id=instance.project_id, assigned_to_id=instance.user_id
    ).update(assigned_to=None, updated_at=timezone.now())
