from datetime import date

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase


class ProjectModelTests(TestCase):
    def test_creating_project_adds_its_owner_as_admin(self):
        self.assertIn("project", apps.all_models["projects"])
        Project = apps.get_model("projects", "Project")
        Membership = apps.get_model("projects", "ProjectMembership")
        owner = get_user_model().objects.create_user("owner@example.com")
        project = Project.objects.create(
            title="Stride launch",
            description="First release",
            deadline=date(2026, 12, 31),
            owner=owner,
        )
        membership = Membership.objects.get(project=project, user=owner)
        self.assertEqual(membership.role, Membership.Role.ADMIN)
        self.assertIn(owner, project.members.all())
        self.assertEqual(str(project), "Stride launch")

    def test_owner_membership_cannot_be_demoted_or_removed(self):
        from django.core.exceptions import ValidationError
        from django.db import transaction

        from projects.models import Project, ProjectMembership

        owner = get_user_model().objects.create_user("owner@example.com")
        project = Project.objects.create(
            title="Stride", deadline=date(2026, 12, 31), owner=owner
        )
        membership = project.memberships.get(user=owner)
        membership.role = ProjectMembership.Role.MEMBER
        with self.assertRaises(ValidationError):
            membership.save()
        with self.assertRaises(ValidationError), transaction.atomic():
            project.memberships.filter(user=owner).delete()
        replacement = get_user_model().objects.create_user("other@example.com")
        project.owner = replacement
        with self.assertRaises(ValidationError):
            project.save()
        project.refresh_from_db()
        project_id = project.pk
        project.delete()
        self.assertFalse(
            ProjectMembership.objects.filter(project_id=project_id).exists()
        )

    def test_membership_changes_keep_assignments_consistent(self):
        from django.core.exceptions import ValidationError
        from django.db import IntegrityError, transaction

        from projects.models import Project, ProjectMembership
        from tasks.models import Task

        User = get_user_model()
        owner = User.objects.create_user("owner@example.com")
        member = User.objects.create_user("member@example.com")
        other = User.objects.create_user("other@example.com")
        inactive = User.objects.create_user("inactive@example.com", is_active=False)
        project = Project.objects.create(
            title="Stride", deadline=date(2026, 12, 31), owner=owner
        )
        membership = ProjectMembership.objects.create(project=project, user=member)
        task = Task.objects.create(
            project=project,
            title="Build board",
            created_by=owner,
            assigned_to=member,
            deadline=date(2026, 12, 20),
        )
        with self.assertRaises(ValidationError):
            ProjectMembership.objects.create(project=project, user=inactive)
        with self.assertRaises(ValidationError):
            ProjectMembership(project=project, user_id=other.pk + 1000).full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProjectMembership.objects.bulk_create(
                [ProjectMembership(project=project, user=member)]
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProjectMembership.objects.filter(pk=membership.pk).update(role="unknown")
        membership.user = other
        with self.assertRaises(ValidationError):
            membership.save()
        membership.refresh_from_db()
        ProjectMembership.objects.filter(pk=membership.pk).delete()
        task.refresh_from_db()
        self.assertIsNone(task.assigned_to_id)
