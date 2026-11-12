from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from projects.models import Project, ProjectMembership
from tasks.models import Task


class MemberManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user("team-owner@example.com")
        cls.member = User.objects.create_user("team-member@example.com")
        cls.project = Project.objects.create(
            title="Team", owner=cls.owner, deadline=date(2026, 12, 31)
        )

    def test_admin_adds_changes_role_and_removes_member_with_unassignment(self):
        self.client.force_login(self.owner)
        base = f"/projects/{self.project.pk}/members/"
        headers = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "project-members"}
        response = self.client.post(
            base, {"email": "TEAM-MEMBER@example.com", "role": "member"}, **headers
        )
        self.assertEqual(response.status_code, 200)
        membership = self.project.memberships.get(user=self.member)
        self.assertNotContains(response, "<!doctype")
        self.assertIn("memberSaved", response.headers["HX-Trigger-After-Swap"])
        self.client.post(base + f"{membership.pk}/role/", {"role": "admin"}, **headers)
        membership.refresh_from_db()
        self.assertEqual(membership.role, "admin")
        task = Task.objects.create(
            project=self.project,
            created_by=self.owner,
            assigned_to=self.member,
            title="Keep task",
            deadline=self.project.deadline,
        )
        remove = base + f"{membership.pk}/remove/"
        self.assertContains(self.client.get(remove), "Remove member")
        self.assertTrue(ProjectMembership.objects.filter(pk=membership.pk).exists())
        self.assertEqual(self.client.post(remove, **headers).status_code, 200)
        task.refresh_from_db()
        self.assertIsNone(task.assigned_to)
        self.assertFalse(ProjectMembership.objects.filter(pk=membership.pk).exists())

    def test_permissions_owner_protection_validation_and_csrf(self):
        membership = ProjectMembership.objects.create(
            project=self.project, user=self.member
        )
        owner_membership = self.project.memberships.get(user=self.owner)
        base = f"/projects/{self.project.pk}/members/"
        self.client.force_login(self.member)
        self.assertEqual(
            self.client.post(
                base, {"email": self.member.email, "role": "admin"}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(base + f"{owner_membership.pk}/remove/").status_code, 403
        )
        self.client.force_login(self.owner)
        for data in (
            {"email": self.member.email, "role": "member"},
            {"email": "unknown@example.com", "role": "member"},
            {"email": self.member.email, "role": "invalid"},
        ):
            page = self.client.post(base, data)
            self.assertTrue(page.context["member_form"].errors)
        self.assertEqual(
            self.client.post(
                base + f"{owner_membership.pk}/role/", {"role": "member"}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(base + f"{owner_membership.pk}/remove/").status_code, 403
        )
        foreign = Project.objects.create(
            title="Other", owner=self.member, deadline=self.project.deadline
        )
        target = foreign.memberships.get(user=self.member)
        self.assertEqual(
            self.client.post(base + f"{target.pk}/remove/").status_code, 404
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(base, {}).status_code, 403)
        self.assertEqual(
            client.post(base + f"{membership.pk}/role/", {"role": "admin"}).status_code,
            403,
        )
        self.assertEqual(
            client.post(base + f"{membership.pk}/remove/").status_code, 403
        )
