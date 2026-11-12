from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from projects.models import Project, ProjectMembership
from tasks.models import Task


class TaskMoveTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user("board-owner@example.com")
        cls.member = User.objects.create_user("board-member@example.com")
        cls.project = Project.objects.create(
            title="Board", owner=cls.owner, deadline=date(2026, 12, 31)
        )
        ProjectMembership.objects.create(project=cls.project, user=cls.member)
        cls.moving = Task.objects.create(
            project=cls.project,
            created_by=cls.member,
            title="Moving task",
            deadline=cls.project.deadline,
        )
        cls.source = Task.objects.create(
            project=cls.project,
            created_by=cls.owner,
            title="Source task",
            deadline=cls.project.deadline,
            position=4,
        )
        cls.first = Task.objects.create(
            project=cls.project,
            created_by=cls.owner,
            title="First review",
            deadline=cls.project.deadline,
            status="review",
        )
        cls.last = Task.objects.create(
            project=cls.project,
            created_by=cls.owner,
            title="Last review",
            deadline=cls.project.deadline,
            status="review",
            position=5,
        )

    def move(self, task, **data):
        return self.client.post(
            f"/projects/{self.project.pk}/tasks/{task.pk}/move/",
            data,
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="project-board",
        )

    def test_member_moves_own_task_before_destination_card_and_persists_order(self):
        self.client.force_login(self.member)
        response = self.move(self.moving, status="review", before_id=self.last.pk)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<!doctype")
        self.assertContains(response, 'id="project-board"')
        self.assertIn("taskMoved", response.headers["HX-Trigger-After-Swap"])
        self.moving.refresh_from_db()
        self.assertEqual(self.moving.status, "review")
        self.assertEqual(
            list(
                self.project.tasks.filter(status="review").values_list("pk", "position")
            ),
            [(self.first.pk, 0), (self.moving.pk, 1), (self.last.pk, 2)],
        )
        self.source.refresh_from_db()
        self.assertEqual(self.source.position, 0)
        board = self.client.get(f"/projects/{self.project.pk}/")
        self.assertEqual(
            [task.pk for task in board.context["columns"][2]["tasks"]],
            [self.first.pk, self.moving.pk, self.last.pk],
        )

    def test_reorders_within_column_and_completion_follows_status(self):
        self.client.force_login(self.owner)
        self.assertEqual(
            self.move(self.last, status="review", before_id=self.first.pk).status_code,
            200,
        )
        self.assertEqual(
            list(
                self.project.tasks.filter(status="review").values_list("pk", flat=True)
            ),
            [self.last.pk, self.first.pk],
        )
        self.move(self.last, status="completed")
        self.last.refresh_from_db()
        completed_at = self.last.completed_at
        self.assertIsNotNone(completed_at)
        self.move(self.last, status="completed")
        self.last.refresh_from_db()
        self.assertEqual(self.last.completed_at, completed_at)
        self.move(self.last, status="todo")
        self.last.refresh_from_db()
        self.assertIsNone(self.last.completed_at)
        self.assertEqual(
            list(self.project.tasks.filter(status="todo").values_list("pk", flat=True)),
            [self.moving.pk, self.source.pk, self.last.pk],
        )

    def test_permissions_apply_to_handles_and_each_move_request(self):
        self.client.force_login(self.member)
        board = self.client.get(f"/projects/{self.project.pk}/")
        self.assertContains(board, f'data-move-task="{self.moving.pk}"')
        self.assertNotContains(board, f'data-move-task="{self.first.pk}"')
        self.assertEqual(self.move(self.first, status="completed").status_code, 403)
        self.first.assigned_to = self.member
        self.first.save()
        self.assertEqual(self.move(self.first, status="completed").status_code, 200)
        self.first.assigned_to = None
        self.first.save()
        self.assertEqual(self.move(self.first, status="review").status_code, 403)
        membership = self.project.memberships.get(user=self.member)
        membership.role = ProjectMembership.Role.ADMIN
        membership.save()
        self.assertEqual(self.move(self.first, status="review").status_code, 200)
        membership.role = ProjectMembership.Role.MEMBER
        membership.save()
        self.assertEqual(self.move(self.first, status="completed").status_code, 403)
        membership.delete()
        self.assertEqual(self.move(self.moving, status="review").status_code, 404)

    def test_bad_or_cross_project_targets_never_mutate_board(self):
        foreign = Project.objects.create(
            title="Other board", owner=self.owner, deadline=self.project.deadline
        )
        foreign_task = Task.objects.create(
            project=foreign,
            created_by=self.owner,
            title="Other task",
            deadline=foreign.deadline,
            status="review",
        )
        self.client.force_login(self.owner)
        fields = ("pk", "status", "position", "completed_at", "updated_at")
        before = list(Task.objects.order_by("pk").values_list(*fields))
        for data, code in (
            ({"status": "unknown"}, 400),
            ({"status": "review", "before_id": "bad"}, 400),
            ({"status": "review", "before_id": -1}, 400),
            ({"status": "review", "before_id": "9" * 100}, 400),
            ({"status": "review", "before_id": self.source.pk}, 409),
            ({"status": "todo", "before_id": self.moving.pk}, 409),
            ({"status": "review", "before_id": foreign_task.pk}, 409),
        ):
            with self.subTest(data=data):
                self.assertEqual(self.move(self.moving, **data).status_code, code)
                self.assertEqual(
                    list(Task.objects.order_by("pk").values_list(*fields)), before
                )
        self.assertEqual(self.move(foreign_task, status="todo").status_code, 404)
        self.move(
            self.moving,
            status="review",
            project=foreign.pk,
            created_by=self.owner.pk,
            title="Tampered",
            position=999,
        )
        self.moving.refresh_from_db()
        self.assertEqual(self.moving.title, "Moving task")
        self.assertEqual(self.moving.created_by, self.member)
        self.assertEqual(self.moving.project, self.project)
        self.assertEqual(self.moving.position, 2)
        self.client.force_login(self.member)
        self.assertEqual(
            self.client.post(
                f"/projects/{foreign.pk}/tasks/{foreign_task.pk}/move/",
                {"status": "todo"},
            ).status_code,
            404,
        )

    def test_move_is_csrf_protected_post_only_with_native_redirect(self):
        from django.test import Client

        self.client.force_login(self.owner)
        url = f"/projects/{self.project.pk}/tasks/{self.moving.pk}/move/"
        self.assertEqual(self.client.get(url).status_code, 405)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(url, {"status": "review"}).status_code, 403)
        self.assertRedirects(
            self.client.post(url, {"status": "review"}),
            f"/projects/{self.project.pk}/",
        )
