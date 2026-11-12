from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from projects.models import Project, ProjectMembership
from tasks.models import Task


class TaskViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user("owner@example.com")
        cls.member = User.objects.create_user("member@example.com")
        cls.other = User.objects.create_user("other@example.com")
        cls.project = Project.objects.create(
            title="Launch", owner=cls.owner, deadline=date(2026, 12, 31)
        )
        ProjectMembership.objects.create(project=cls.project, user=cls.member)
        ProjectMembership.objects.create(project=cls.project, user=cls.other)

    def test_member_creates_task_with_scoped_assignees_and_refreshes_board(self):
        self.client.force_login(self.member)
        url = f"/projects/{self.project.pk}/tasks/new/"
        modal = self.client.get(
            url, HTTP_HX_REQUEST="true", HTTP_HX_TARGET="task-dialog-content"
        )
        self.assertEqual(modal.status_code, 200)
        self.assertNotContains(modal, "<!doctype")
        self.assertContains(modal, "New task")
        self.assertEqual(
            modal.context["form"].initial["deadline"], self.project.deadline
        )
        response = self.client.post(
            url,
            {
                "title": "  Build board  ",
                "description": "A clear next step",
                "assigned_to": self.other.pk,
                "priority": "high",
                "deadline": "2026-12-20",
                "status": "review",
                "project": 999,
                "created_by": self.owner.pk,
                "position": 999,
            },
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="task-dialog-content",
        )
        self.assertEqual(response.status_code, 200)
        task = Task.objects.get(title="Build board")
        self.assertEqual(task.project, self.project)
        self.assertEqual(task.created_by, self.member)
        self.assertEqual(task.assigned_to, self.other)
        self.assertEqual(task.status, "review")
        self.assertNotEqual(task.position, 999)
        self.assertContains(response, 'hx-swap-oob="outerHTML"')
        self.assertIn("taskSaved", response.headers["HX-Trigger-After-Swap"])
        self.assertContains(
            self.client.get(f"/projects/{self.project.pk}/"), "Build board"
        )

    def test_creator_edits_status_and_completion_while_preserving_identity(self):
        task = Task.objects.create(
            project=self.project,
            created_by=self.member,
            title="Build board",
            deadline=date(2026, 12, 20),
        )
        tail = Task.objects.create(
            project=self.project,
            created_by=self.owner,
            title="Review tail",
            deadline=date(2026, 12, 20),
            status="review",
            position=7,
        )
        self.client.force_login(self.member)
        url = f"/projects/{self.project.pk}/tasks/{task.pk}/edit/"
        self.assertContains(self.client.get(url), "<!doctype")
        data = {
            "title": "Updated board",
            "description": "<script>alert(1)</script>",
            "assigned_to": self.other.pk,
            "priority": "critical",
            "deadline": "2026-12-21",
            "status": "completed",
            "created_by": self.owner.pk,
            "project": 999,
            "position": 999,
        }
        self.assertRedirects(
            self.client.post(url, data), f"/projects/{self.project.pk}/"
        )
        task.refresh_from_db()
        self.assertIsNotNone(task.completed_at)
        self.assertEqual(task.created_by, self.member)
        self.assertEqual(task.project, self.project)
        self.assertEqual(task.priority, "critical")
        self.assertContains(
            self.client.get(f"/projects/{self.project.pk}/tasks/{task.pk}/"),
            "&lt;script&gt;alert(1)&lt;/script&gt;",
        )
        data["status"] = "review"
        self.client.post(url, data)
        task.refresh_from_db()
        self.assertIsNone(task.completed_at)
        self.assertEqual(task.position, tail.position + 1)

    def test_admin_creator_and_assignee_can_confirm_deletion(self):
        for actor in (self.owner, self.other, self.member):
            with self.subTest(actor=actor.pk):
                task = Task.objects.create(
                    project=self.project,
                    created_by=self.other,
                    assigned_to=self.member,
                    title="Remove this task",
                    deadline=date(2026, 12, 20),
                )
                self.client.force_login(actor)
                url = f"/projects/{self.project.pk}/tasks/{task.pk}/delete/"
                self.assertContains(self.client.get(url), "Delete this task?")
                self.assertTrue(Task.objects.filter(pk=task.pk).exists())
                response = self.client.post(
                    url, HTTP_HX_REQUEST="true", HTTP_HX_TARGET="task-dialog-content"
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(Task.objects.filter(pk=task.pk).exists())
                self.assertContains(response, "0 tasks")
                self.assertIn(
                    "Task deleted.", response.headers["HX-Trigger-After-Swap"]
                )

    def test_unrelated_members_can_read_but_cannot_manage_and_ids_stay_scoped(self):
        task = Task.objects.create(
            project=self.project,
            created_by=self.owner,
            title="Team context",
            description="Full task details",
            deadline=date(2026, 12, 20),
        )
        self.client.force_login(self.member)
        base = f"/projects/{self.project.pk}/tasks/{task.pk}/"
        page = self.client.get(base)
        self.assertContains(page, "Full task details")
        self.assertContains(page, "View only")
        self.assertNotContains(page, "Save changes")
        self.assertNotContains(page, "Delete task")
        for suffix in ("edit/", "delete/"):
            for method in (self.client.get, self.client.post):
                self.assertEqual(method(base + suffix).status_code, 403)
        private = Project.objects.create(
            title="Private", owner=self.other, deadline=date(2026, 12, 31)
        )
        private_task = Task.objects.create(
            project=private,
            created_by=self.other,
            title="Private task",
            deadline=date(2026, 12, 20),
        )
        for path in (
            f"/projects/{private.pk}/tasks/new/",
            f"/projects/{self.project.pk}/tasks/{private_task.pk}/",
            f"/projects/{self.project.pk}/tasks/{private_task.pk}/edit/",
            f"/projects/{self.project.pk}/tasks/{private_task.pk}/delete/",
        ):
            self.assertEqual(self.client.get(path).status_code, 404)
        task.assigned_to = self.member
        task.save()
        self.assertContains(self.client.get(base), "Save changes")
        data = {
            "title": task.title,
            "description": "",
            "priority": "medium",
            "deadline": "2026-12-20",
            "status": "todo",
            "assigned_to": "",
        }
        self.client.post(base + "edit/", data)
        self.assertEqual(self.client.get(base + "edit/").status_code, 403)
        membership = self.project.memberships.get(user=self.member)
        membership.role = ProjectMembership.Role.ADMIN
        membership.save()
        self.assertContains(self.client.get(base + "edit/"), "Save changes")

    def test_invalid_input_and_outside_or_inactive_assignees_do_not_save(self):
        User = get_user_model()
        outsider = User.objects.create_user("outsider@example.com")
        inactive = User.objects.create_user("inactive@example.com")
        ProjectMembership.objects.create(project=self.project, user=inactive)
        inactive.is_active = False
        inactive.save()
        self.client.force_login(self.member)
        url = f"/projects/{self.project.pk}/tasks/new/"
        page = self.client.get(url)
        self.assertNotContains(page, "outsider@example.com")
        self.assertNotContains(page, "inactive@example.com")
        data = {
            "title": "Task",
            "description": "Keep this draft",
            "assigned_to": "",
            "priority": "medium",
            "deadline": "2026-12-20",
            "status": "todo",
        }
        for changes in (
            {"title": "   "},
            {"deadline": "invalid"},
            {"priority": "urgent"},
            {"status": "unknown"},
            {"assigned_to": outsider.pk},
            {"assigned_to": inactive.pk},
        ):
            with self.subTest(changes=changes):
                response = self.client.post(
                    url,
                    data | changes,
                    HTTP_HX_REQUEST="true",
                    HTTP_HX_TARGET="task-dialog-content",
                )
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assertContains(response, "Keep this draft")
                self.assertNotIn("HX-Trigger-After-Swap", response.headers)
        self.assertFalse(Task.objects.exists())

    def test_task_writes_require_csrf(self):
        from django.test import Client

        task = Task.objects.create(
            project=self.project,
            created_by=self.owner,
            title="Keep task",
            deadline=date(2026, 12, 20),
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        for path in (
            f"/projects/{self.project.pk}/tasks/new/",
            f"/projects/{self.project.pk}/tasks/{task.pk}/edit/",
            f"/projects/{self.project.pk}/tasks/{task.pk}/delete/",
        ):
            self.assertEqual(client.post(path, {}).status_code, 403)
        task.refresh_from_db()
        self.assertEqual(task.title, "Keep task")
        self.assertEqual(Task.objects.count(), 1)
