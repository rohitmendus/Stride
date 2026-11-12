from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from projects.models import Project, ProjectMembership
from tasks.models import Task


class TaskWorkspaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(
            "workspace-owner@example.com", first_name="Alex Lee"
        )
        cls.member = User.objects.create_user(
            "workspace-member@example.com", first_name="Jamie Kim"
        )
        cls.project = Project.objects.create(
            title="Launch", owner=cls.owner, deadline=date(2026, 12, 31)
        )
        ProjectMembership.objects.create(project=cls.project, user=cls.member)
        cls.mine = Task.objects.create(
            project=cls.project,
            created_by=cls.owner,
            assigned_to=cls.owner,
            title="Build onboarding",
            description="A clear first step",
            priority="high",
            deadline=date(2026, 1, 1),
        )
        cls.other = Task.objects.create(
            project=cls.project,
            created_by=cls.member,
            assigned_to=cls.member,
            title="Review mobile",
            priority="medium",
            status="review",
            deadline=cls.project.deadline,
        )
        cls.unassigned = Task.objects.create(
            project=cls.project,
            created_by=cls.owner,
            title="Release notes",
            description="Onboarding documentation",
            priority="low",
            deadline=cls.project.deadline,
        )

    def test_search_filters_and_list_use_real_project_tasks_and_counts(self):
        self.client.force_login(self.owner)
        url = f"/projects/{self.project.pk}/"
        page = self.client.get(
            url,
            {
                "q": "onboarding",
                "priority": "high",
                "assignee": str(self.owner.pk),
                "view": "list",
            },
        )
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.context["task_count"], 3)
        self.assertIn("visible_count", page.context)
        self.assertEqual(page.context["visible_count"], 1)
        self.assertEqual(page.context["my_task_count"], 1)
        self.assertEqual(
            [task.pk for task in page.context["visible_tasks"]], [self.mine.pk]
        )
        self.assertEqual(page.context["board_options"]["view"], "list")
        self.assertTrue(page.context["visible_tasks"][0].is_overdue)
        self.assertEqual(page.context["visible_tasks"][0].assignee_initials, "AL")
        self.assertEqual(
            [
                task.pk
                for task in self.client.get(url, {"assignee": "unassigned"}).context[
                    "visible_tasks"
                ]
            ],
            [self.unassigned.pk],
        )
        self.assertEqual(
            [
                task.pk
                for task in self.client.get(url, {"mine": "1"}).context["visible_tasks"]
            ],
            [self.mine.pk],
        )
        self.assertEqual(
            [
                task.pk
                for task in self.client.get(
                    url, {"q": f"STR-{self.other.pk:03d}"}
                ).context["visible_tasks"]
            ],
            [self.other.pk],
        )

    def test_column_creation_and_saves_preserve_view_filters_and_notify(self):
        import json

        self.client.force_login(self.owner)
        query = "status=review&view=list&priority=high&mine=1"
        create = f"/projects/{self.project.pk}/tasks/new/?{query}"
        headers = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "task-dialog-content"}
        page = self.client.get(create, **headers)
        self.assertEqual(page.context["form"].initial["status"], "review")
        self.assertIn("view=list", page.context["form_action"])
        data = {
            "title": "A new high task",
            "description": "",
            "status": "review",
            "priority": "high",
            "assigned_to": self.owner.pk,
            "deadline": "2026-12-31",
        }
        response = self.client.post(create, data, **headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["board_options"]["view"], "list")
        self.assertEqual(response.context["visible_count"], 2)
        event = json.loads(response.headers["HX-Trigger-After-Swap"])["taskSaved"]
        self.assertEqual(event["message"], "Task added to the board")
        task = Task.objects.get(pk=event["task_id"])
        edit = f"/projects/{self.project.pk}/tasks/{task.pk}/edit/?view=list&mine=1&priority=high"
        data["status"] = "completed"
        response = self.client.post(edit, data, **headers)
        event = json.loads(response.headers["HX-Trigger-After-Swap"])["taskSaved"]
        self.assertEqual(event["message"], "Moved to Completed")
        self.assertEqual(response.context["board_options"]["mine"], "1")
        response = self.client.post(
            f"/projects/{self.project.pk}/tasks/{task.pk}/move/?view=list&priority=high&mine=1",
            {"status": "todo"},
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="project-board",
        )
        self.assertEqual(response.context["board_options"]["view"], "list")
        self.assertEqual(response.context["my_task_count"], 2)
        self.assertRedirects(
            self.client.post(edit, data),
            f"/projects/{self.project.pk}/?priority=high&mine=1&view=list",
        )

    def test_filtered_fragments_stay_private_and_unknown_parameters_are_ignored(self):
        private = Project.objects.create(
            title="Private board", owner=self.member, deadline=self.project.deadline
        )
        Task.objects.create(
            project=private,
            created_by=self.member,
            title="Private task",
            deadline=private.deadline,
        )
        self.client.force_login(self.owner)
        response = self.client.get(
            f"/projects/{self.project.pk}/",
            {
                "q": "missing",
                "view": "list",
                "project": private.pk,
                "next": "https://example.test",
            },
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="project-board",
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<!doctype")
        self.assertNotContains(response, "Private task")
        self.assertEqual(response.context["visible_count"], 0)
        self.assertNotIn("next", response.context["board_query"])
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertIn("HX-Target", response.headers["Vary"])
        self.assertEqual(
            self.client.get(
                f"/projects/{private.pk}/", {"view": "list", "mine": "1"}
            ).status_code,
            404,
        )

    def test_my_tasks_span_member_projects_and_dialog_writes_keep_personal_scope(self):
        other_project = Project.objects.create(
            title="Second launch", owner=self.member, deadline=self.project.deadline
        )
        ProjectMembership.objects.create(project=other_project, user=self.owner)
        assigned = Task.objects.create(
            project=other_project,
            created_by=self.member,
            assigned_to=self.owner,
            title="Assigned in second project",
            deadline=other_project.deadline,
        )
        self.client.force_login(self.owner)
        page = self.client.get("/projects/my-tasks/")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(
            {task.pk for task in page.context["visible_tasks"]},
            {self.mine.pk, assigned.pk},
        )
        self.assertEqual(page.context["sidebar_my_task_count"], 2)
        self.assertContains(page, "Second launch")
        response = self.client.post(
            f"/projects/{other_project.pk}/tasks/{assigned.pk}/edit/?workspace=mine",
            {
                "title": assigned.title,
                "description": "",
                "status": "completed",
                "priority": "medium",
                "assigned_to": self.member.pk,
                "deadline": "2026-12-31",
            },
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="task-dialog-content",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["personal_workspace"])
        self.assertEqual(
            [task.pk for task in response.context["visible_tasks"]], [self.mine.pk]
        )
        self.assertNotContains(response, "Assigned in second project")
        self.assertEqual(response.context["sidebar_my_task_count"], 1)
