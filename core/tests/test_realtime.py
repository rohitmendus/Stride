from datetime import timedelta
from unittest.mock import AsyncMock, patch

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from projects.models import Project, ProjectMembership
from tasks.models import Task


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
)
class DashboardRealtimeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("realtime-owner@example.test")
        cls.member = get_user_model().objects.create_user(
            "realtime-member@example.test"
        )
        cls.project = Project.objects.create(
            owner=cls.owner,
            title="Live project",
            deadline=timezone.localdate() + timedelta(days=7),
        )
        ProjectMembership.objects.create(project=cls.project, user=cls.member)

    def test_task_notifications_are_commit_only_and_redis_failure_does_not_break_save(
        self,
    ):
        layer = get_channel_layer()
        with patch.object(layer, "group_send", new_callable=AsyncMock) as send:
            with self.captureOnCommitCallbacks(execute=True):
                task = Task.objects.create(
                    project=self.project,
                    created_by=self.owner,
                    title="Live task",
                    deadline=self.project.deadline,
                )
                self.assertEqual(send.await_count, 0)
            self.assertEqual(send.await_count, 2)
            for user in (self.owner, self.member):
                send.assert_any_await(
                    f"dashboard.user.{user.pk}", {"type": "dashboard.changed"}
                )
            send.reset_mock()
            with (
                self.captureOnCommitCallbacks(execute=True),
                self.assertRaises(ValueError),
                transaction.atomic(),
            ):
                task.title = "Rolled back"
                task.save()
                raise ValueError("rollback")
            send.assert_not_awaited()
            send.side_effect = ConnectionError("Redis unavailable")
            with self.captureOnCommitCallbacks(execute=True):
                task.title = "Still saved"
                task.save()
            task.refresh_from_db()
            self.assertEqual(task.title, "Still saved")

    def test_removed_members_and_deleted_project_members_get_refreshes(self):
        with patch.object(
            get_channel_layer(), "group_send", new_callable=AsyncMock
        ) as send:
            with self.captureOnCommitCallbacks(execute=True):
                ProjectMembership.objects.get(
                    project=self.project, user=self.member
                ).delete()
            self.assertEqual(
                {call.args[0] for call in send.await_args_list},
                {f"dashboard.user.{self.owner.pk}", f"dashboard.user.{self.member.pk}"},
            )
            ProjectMembership.objects.create(project=self.project, user=self.member)
            send.reset_mock()
            with self.captureOnCommitCallbacks(execute=True):
                self.project.delete()
            self.assertEqual(
                {call.args[0] for call in send.await_args_list},
                {f"dashboard.user.{self.owner.pk}", f"dashboard.user.{self.member.pk}"},
            )


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
)
class DashboardSocketTests(TransactionTestCase):
    def test_socket_auth_origin_and_expired_session(self):
        from config.asgi import application

        self.assertTrue(
            hasattr(application, "application_mapping"), "WebSocket routing is missing"
        )
        self.owner = get_user_model().objects.create_user("socket-owner@example.test")
        self.client.force_login(self.owner)
        session_key = self.client.cookies[settings.SESSION_COOKIE_NAME].value

        async def check():
            headers = [
                (b"origin", b"http://localhost"),
                (b"cookie", f"{settings.SESSION_COOKIE_NAME}={session_key}".encode()),
            ]
            with override_settings(ALLOWED_HOSTS=["localhost"], DEBUG=False):
                anonymous = WebsocketCommunicator(
                    application, "/ws/dashboard/", headers=headers[:1]
                )
                self.assertFalse((await anonymous.connect())[0])
                await anonymous.disconnect()
                evil = WebsocketCommunicator(
                    application,
                    "/ws/dashboard/",
                    headers=[(b"origin", b"https://evil.example"), headers[1]],
                )
                self.assertFalse((await evil.connect())[0])
                await evil.disconnect()
                socket = WebsocketCommunicator(
                    application, "/ws/dashboard/", headers=headers
                )
                self.assertTrue((await socket.connect())[0])
                await get_channel_layer().group_send(
                    f"dashboard.user.{self.owner.pk}", {"type": "dashboard.changed"}
                )
                self.assertEqual(
                    await socket.receive_json_from(), {"type": "dashboard.changed"}
                )
                await database_sync_to_async(
                    Session.objects.filter(session_key=session_key).delete
                )()
                await get_channel_layer().group_send(
                    f"dashboard.user.{self.owner.pk}", {"type": "dashboard.changed"}
                )
                closed = await socket.receive_output()
                self.assertEqual(closed["type"], "websocket.close")
                self.assertEqual(closed["code"], 4401)
                await socket.disconnect()

        async_to_sync(check)()
