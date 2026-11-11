from datetime import date

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from projects.models import Project, ProjectMembership


class TaskModelTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("owner@example.com")
        self.member = get_user_model().objects.create_user("member@example.com")
        self.project = Project.objects.create(
            title="Stride", deadline=date(2026, 12, 31), owner=self.owner
        )
        ProjectMembership.objects.create(project=self.project, user=self.member)

    def test_assignment_requires_an_active_member_of_the_same_project(self):
        self.assertIn("task", apps.all_models["tasks"])
        Task = apps.get_model("tasks", "Task")
        task = Task.objects.create(
            project=self.project,
            title="Build board",
            created_by=self.owner,
            assigned_to=self.member,
            deadline=date(2026, 12, 20),
        )
        self.assertEqual(task.priority, Task.Priority.MEDIUM)
        self.assertEqual(task.status, Task.Status.TODO)
        self.assertEqual(task.position, 0)
        outsider = get_user_model().objects.create_user("outsider@example.com")
        task.assigned_to = outsider
        with self.assertRaises(ValidationError):
            task.save()
        task.assigned_to = self.member
        self.member.is_active = False
        self.member.save()
        with self.assertRaises(ValidationError):
            task.save()

    def test_completion_timestamp_tracks_status_changes(self):
        Task = apps.get_model("tasks", "Task")
        task = Task.objects.create(
            project=self.project,
            title="Finish board",
            created_by=self.owner,
            deadline=date(2026, 12, 20),
        )
        self.assertIsNone(task.completed_at)
        task.status = Task.Status.COMPLETED
        task.save(update_fields={"status"})
        task.refresh_from_db()
        self.assertIsNotNone(task.completed_at)
        completed_at = task.completed_at
        task.title = "Finished board"
        task.save(update_fields={"title"})
        task.refresh_from_db()
        self.assertEqual(task.completed_at, completed_at)
        task.status = Task.Status.REVIEW
        task.save(update_fields={"status"})
        task.refresh_from_db()
        self.assertIsNone(task.completed_at)
