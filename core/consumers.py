import asyncio
from contextlib import suppress
from importlib import import_module
from types import SimpleNamespace

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.contrib.auth import get_user
from redis.exceptions import RedisError


class DashboardConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.watcher = None
        self.group_name = None
        user = self.scope["user"]
        if not user.is_authenticated or not await self.session_valid():
            await self.close(code=4401)
            return
        self.group_name = f"dashboard.user.{user.pk}"
        try:
            await asyncio.wait_for(
                self.channel_layer.group_add(self.group_name, self.channel_name), 2
            )
        except (RedisError, OSError):
            await self.close(code=1013)
            return
        await self.accept()
        self.watcher = asyncio.create_task(self.watch_session())

    @database_sync_to_async
    def session_valid(self):
        key = self.scope["session"].session_key
        if not key:
            return False
        store = import_module(settings.SESSION_ENGINE).SessionStore(session_key=key)
        user = get_user(SimpleNamespace(session=store))
        return user.is_authenticated and user.pk == self.scope["user"].pk

    async def watch_session(self):
        while True:
            await asyncio.sleep(20)
            if not await self.session_valid():
                await self.close(code=4401)
                return
            try:
                await asyncio.wait_for(
                    self.channel_layer.group_add(self.group_name, self.channel_name), 2
                )
            except (RedisError, OSError):
                await self.close(code=1013)
                return
            await self.send_json({"type": "ping"})

    async def receive_json(self, content, **kwargs):
        if not isinstance(content, dict) or content.get("type") != "pong":
            await self.close(code=4400)

    async def dashboard_changed(self, event):
        if not await self.session_valid():
            await self.close(code=4401)
            return
        await self.send_json({"type": "dashboard.changed"})

    async def notifications_changed(self, event):
        if not await self.session_valid():
            await self.close(code=4401)
            return
        await self.send_json({"type": "notifications.changed"})

    async def disconnect(self, code):
        if self.watcher:
            self.watcher.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await self.watcher
        if self.group_name:
            with suppress(Exception):
                await asyncio.wait_for(
                    self.channel_layer.group_discard(
                        self.group_name, self.channel_name
                    ),
                    2,
                )
