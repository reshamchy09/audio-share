import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer

AUDIO_GROUP = "live_audio"
BROWSER_GROUP = "live_browser"

class AudioConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(AUDIO_GROUP, self.channel_name)
        await self.accept()
        self.keepalive_task = asyncio.ensure_future(self.send_keepalive())

    async def disconnect(self, code):
        self.keepalive_task.cancel()
        await self.channel_layer.group_discard(AUDIO_GROUP, self.channel_name)

    async def send_keepalive(self):
        while True:
            await asyncio.sleep(30)  # ping every 30 seconds
            try:
                await self.send(text_data=json.dumps({"type": "ping"}))
            except Exception:
                break

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data:
            await self.channel_layer.group_send(
                BROWSER_GROUP,
                {"type": "audio.frame", "data": bytes_data.hex()}
            )

    async def audio_frame(self, event):
        pass

    async def control_command(self, event):
        await self.send(text_data=json.dumps({"command": event["command"]}))


class BrowserConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(BROWSER_GROUP, self.channel_name)
        await self.accept()
        self.keepalive_task = asyncio.ensure_future(self.send_keepalive())

    async def disconnect(self, code):
        self.keepalive_task.cancel()
        await self.channel_layer.group_discard(BROWSER_GROUP, self.channel_name)

    async def send_keepalive(self):
        while True:
            await asyncio.sleep(30)
            try:
                await self.send(text_data=json.dumps({"type": "ping"}))
            except Exception:
                break

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            data = json.loads(text_data)
            if data.get("type") == "pong":
                return  # ignore pong replies
            await self.channel_layer.group_send(
                AUDIO_GROUP,
                {"type": "control.command", "command": data.get("command")}
            )

    async def audio_frame(self, event):
        await self.send(text_data=json.dumps({"audio": event["data"]}))
