from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from projects.models import Project


class ProjectViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            "owner@example.com", first_name="Alex"
        )
        cls.other = get_user_model().objects.create_user("other@example.com")
        cls.private = Project.objects.create(
            title="Private project", owner=cls.other, deadline=date(2026, 12, 31)
        )

    def test_create_and_list_are_scoped_to_the_signed_in_user(self):
        self.client.force_login(self.owner)
        self.assertContains(self.client.get("/projects/"), "Your projects")
        self.assertNotContains(self.client.get("/projects/"), "Private project")
        response = self.client.post(
            "/projects/new/",
            {
                "title": "  Launch site  ",
                "description": "A focused release",
                "deadline": "2026-12-20",
                "owner": self.other.pk,
            },
        )
        project = Project.objects.get(title="Launch site")
        self.assertRedirects(response, f"/projects/{project.pk}/")
        self.assertEqual(project.owner, self.owner)
        self.assertEqual(project.memberships.get(user=self.owner).role, "admin")
        self.assertContains(self.client.get("/"), "Launch site")
        self.assertContains(
            self.client.get(f"/projects/{project.pk}/"), "A focused release"
        )

    def test_owner_can_edit_and_confirm_deletion_with_cascades(self):
        from tasks.models import Task

        project = Project.objects.create(
            title="Launch", owner=self.owner, deadline=date(2026, 12, 31)
        )
        task = Task.objects.create(
            title="Build",
            project=project,
            created_by=self.owner,
            deadline=date(2026, 12, 20),
        )
        self.client.force_login(self.owner)
        self.assertEqual(
            self.client.get(f"/projects/{project.pk}/edit/").status_code, 200
        )
        response = self.client.post(
            f"/projects/{project.pk}/edit/",
            {
                "title": "Updated launch",
                "description": "<script>alert(1)</script>",
                "deadline": "2026-12-25",
                "owner": self.other.pk,
            },
        )
        self.assertRedirects(response, f"/projects/{project.pk}/")
        project.refresh_from_db()
        self.assertEqual(project.title, "Updated launch")
        self.assertEqual(project.owner, self.owner)
        self.assertContains(
            self.client.get(f"/projects/{project.pk}/"),
            "&lt;script&gt;alert(1)&lt;/script&gt;",
        )
        self.assertEqual(
            self.client.get(f"/projects/{project.pk}/delete/").status_code, 200
        )
        pk = project.pk
        self.assertTrue(Project.objects.filter(pk=pk).exists())
        self.assertRedirects(self.client.post(f"/projects/{pk}/delete/"), "/")
        self.assertFalse(Project.objects.filter(pk=pk).exists())
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    def test_members_can_read_admins_can_edit_and_only_owners_can_delete(self):
        from projects.models import ProjectMembership

        self.client.force_login(self.owner)
        for suffix in ("", "edit/", "delete/"):
            for method in (self.client.get, self.client.post):
                expected = 405 if not suffix and method == self.client.post else 404
                self.assertEqual(
                    method(f"/projects/{self.private.pk}/{suffix}").status_code,
                    expected,
                )
        membership = ProjectMembership.objects.create(
            project=self.private, user=self.owner
        )
        page = self.client.get(f"/projects/{self.private.pk}/")
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, "Edit project")
        self.assertNotContains(page, "Delete project")
        for suffix in ("edit/", "delete/"):
            for method in (self.client.get, self.client.post):
                self.assertEqual(
                    method(f"/projects/{self.private.pk}/{suffix}").status_code, 403
                )
        membership.role = ProjectMembership.Role.ADMIN
        membership.save()
        self.assertContains(
            self.client.get(f"/projects/{self.private.pk}/"), "Edit project"
        )
        self.assertRedirects(
            self.client.post(
                f"/projects/{self.private.pk}/edit/",
                {"title": "Admin edit", "description": "", "deadline": "2026-12-20"},
            ),
            f"/projects/{self.private.pk}/",
        )
        self.assertEqual(
            self.client.post(f"/projects/{self.private.pk}/delete/").status_code, 403
        )

    def test_invalid_forms_and_missing_csrf_do_not_mutate_projects(self):
        self.client.force_login(self.owner)
        for changes in ({"title": "   "}, {"deadline": "not-a-date"}):
            response = self.client.post(
                "/projects/new/",
                {"title": "Launch", "description": "", "deadline": "2026-12-20"}
                | changes,
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.other)
        for path in (
            "/projects/new/",
            f"/projects/{self.private.pk}/edit/",
            f"/projects/{self.private.pk}/delete/",
        ):
            self.assertEqual(client.post(path, {}).status_code, 403)
        self.assertEqual(Project.objects.count(), 1)

    def test_expired_htmx_sessions_trigger_a_full_login_navigation(self):
        response = self.client.get("/projects/", HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["HX-Redirect"], "/login/?next=/projects/")
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertRedirects(
            self.client.get("/projects/"),
            "/login/?next=/projects/",
            fetch_redirect_response=False,
        )
