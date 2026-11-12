from datetime import timedelta

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from projects.models import Project, ProjectMembership
from tasks.models import Task


class NotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            "notify-owner@example.test", first_name="Alex"
        )
        cls.member = get_user_model().objects.create_user(
            "notify-member@example.test", first_name="Jamie"
        )
        cls.project = Project.objects.create(
            owner=cls.owner,
            title="Notification project",
            deadline=timezone.localdate() + timedelta(days=7),
        )
        ProjectMembership.objects.create(project=cls.project, user=cls.member)

    def test_assignments_are_persisted_without_duplicates_or_self_notifications(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get("/notifications/").status_code, 200)
        data = {
            "title": "Assigned task",
            "description": "",
            "assigned_to": self.member.pk,
            "status": "todo",
            "priority": "medium",
            "deadline": self.project.deadline.isoformat(),
        }
        self.client.post(f"/projects/{self.project.pk}/tasks/new/", data)
        Notification = apps.get_model("core", "Notification")
        notification = Notification.objects.get(recipient=self.member)
        self.assertEqual(notification.actor_id, self.owner.pk)
        self.assertEqual(notification.kind, "task_assigned")
        task = Task.objects.get(title="Assigned task")
        self.client.post(f"/projects/{self.project.pk}/tasks/{task.pk}/edit/", data)
        self.assertEqual(Notification.objects.count(), 1)
        data["title"] = "Self-assigned task"
        data["assigned_to"] = self.owner.pk
        self.client.post(f"/projects/{self.project.pk}/tasks/new/", data)
        self.assertEqual(Notification.objects.count(), 1)
        self.client.force_login(self.member)
        response = self.client.get("/notifications/")
        self.assertContains(response, "Assigned task")
        self.assertEqual(response.context["notification_unread_count"], 1)
        page = self.client.get("/")
        self.assertContains(page, 'id="workspace-notifications"')
        self.assertContains(page, 'data-workspace-socket="/ws/workspace/"')
        self.assertNotContains(page, 'class="app-account"')

    def test_project_addition_and_read_actions(self):
        recipient = get_user_model().objects.create_user("new-notify@example.test")
        self.client.force_login(self.owner)
        self.client.post(
            f"/projects/{self.project.pk}/members/",
            {"email": recipient.email, "role": "member"},
        )
        Notification = apps.get_model("core", "Notification")
        item = Notification.objects.get(recipient=recipient)
        self.assertEqual(item.kind, "project_added")
        url = f"/notifications/{item.pk}/open/"
        self.assertEqual(self.client.post(url).status_code, 404)
        self.client.force_login(recipient)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertRedirects(self.client.post(url), f"/projects/{self.project.pk}/")
        item.refresh_from_db()
        self.assertIsNotNone(item.read_at)
        response = self.client.post("/notifications/read-all/", HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["notification_unread_count"], 0)

    def test_revoked_access_and_csrf(self):
        Notification = apps.get_model("core", "Notification")
        item = Notification.objects.create(
            recipient=self.member,
            actor=self.owner,
            project=self.project,
            kind="project_added",
            message="Private project notification",
        )
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.member)
        self.assertEqual(secure.post("/notifications/read-all/").status_code, 403)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get("/notifications/read-all/").status_code, 405)
        ProjectMembership.objects.get(project=self.project, user=self.member).delete()
        response = self.client.get("/notifications/")
        self.assertNotContains(response, item.message)
        self.assertEqual(response.context["notification_unread_count"], 0)
        self.assertEqual(
            self.client.post(f"/notifications/{item.pk}/open/").status_code, 404
        )
