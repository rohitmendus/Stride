from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from projects.models import Project, ProjectMembership
from tasks.models import Task


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("dashboard@example.test")
        cls.other = get_user_model().objects.create_user("other-dashboard@example.test")
        today = timezone.localdate()
        cls.project = Project.objects.create(
            owner=cls.user,
            title="Dashboard project",
            deadline=today + timedelta(days=7),
        )
        cls.shared = Project.objects.create(
            owner=cls.other, title="Shared project", deadline=cls.project.deadline
        )
        ProjectMembership.objects.create(project=cls.shared, user=cls.user)
        for status, offset, project in (
            ("todo", 0, cls.project),
            ("review", -1, cls.project),
            ("completed", -1, cls.project),
            ("in_progress", 1, cls.shared),
        ):
            Task.objects.create(
                project=project,
                created_by=project.owner,
                title=f"{status} task",
                status=status,
                deadline=today + timedelta(days=offset),
            )
        private = Project.objects.create(
            owner=cls.other, title="Private project", deadline=cls.project.deadline
        )
        Task.objects.create(
            project=private, created_by=cls.other, title="Private task", deadline=today
        )

    def test_dashboard_counts_member_project_tasks_and_excludes_completed_overdue(self):
        self.client.force_login(self.user)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        summary = response.context["summary"]
        self.assertEqual(
            {key: summary[key] for key in ("total", "completed", "pending", "overdue")},
            {"total": 4, "completed": 1, "pending": 3, "overdue": 1},
        )
        self.assertEqual(
            [row["count"] for row in response.context["chart"]], [1, 1, 1, 1]
        )
        self.assertEqual(
            [task.title for task in response.context["overdue_tasks"]], ["review task"]
        )
        self.assertEqual(
            [task.title for task in response.context["upcoming_tasks"]],
            ["todo task", "in_progress task"],
        )
        self.assertContains(response, 'id="dashboard-content"')
        self.assertNotContains(response, "every 15s")
        self.assertContains(response, "dashboardChanged")
        self.assertNotContains(response, "Private task")

    def test_dashboard_refresh_rechecks_access_and_handles_empty_and_anonymous_users(
        self,
    ):
        self.client.force_login(self.user)
        headers = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "dashboard-content"}
        ProjectMembership.objects.get(project=self.shared, user=self.user).delete()
        response = self.client.get("/dashboard/", **headers)
        self.assertEqual(response.context["summary"]["total"], 3)
        self.assertNotContains(response, "<!doctype")
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertIn("HX-Target", response.headers["Vary"])
        empty = get_user_model().objects.create_user("empty-dashboard@example.test")
        self.client.force_login(empty)
        response = self.client.get("/dashboard/", **headers)
        self.assertEqual(response.context["summary"]["total"], 0)
        self.assertEqual(
            [row["percent"] for row in response.context["chart"]], [0, 0, 0, 0]
        )
        self.assertContains(response, "No tasks yet")
        self.client.logout()
        response = self.client.get("/dashboard/", **headers)
        self.assertIn("HX-Redirect", response.headers)
        self.assertEqual(settings.LOGIN_REDIRECT_URL, "core:dashboard")
