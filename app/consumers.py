import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer

AUDIO_GROUP = "live_audio"
BROWSER_GROUP = "live_browser"


class AudioConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(AUDIO_GROUP, self.channel_name)
        await self.accept()
        self.is_streaming = False  # <-- track stream state
        self.keepalive_task = asyncio.ensure_future(self.send_keepalive())

    async def disconnect(self, code):
        self.keepalive_task.cancel()
        await self.channel_layer.group_discard(AUDIO_GROUP, self.channel_name)

    async def send_keepalive(self):
        while True:
            await asyncio.sleep(30)
            try:
                await self.send(text_data=json.dumps({"type": "ping"}))
            except Exception:
                break

    async def receive(self, text_data=None, bytes_data=None):
        # Handle control messages sent by the audio client itself (e.g. pong)
        if text_data:
            data = json.loads(text_data)
            if data.get("type") == "pong":
                return

        # Only forward audio frames when streaming is active
        if bytes_data:
            if self.is_streaming:
                await self.channel_layer.group_send(
                    BROWSER_GROUP,
                    {"type": "audio.frame", "data": bytes_data.hex()}
                )

    async def audio_frame(self, event):
        pass  # AudioConsumer doesn't need to receive audio frames

    async def control_command(self, event):
        command = event.get("command")

        # Update local streaming state
        if command == "start":
            self.is_streaming = True
        elif command == "stop":
            self.is_streaming = False

        # Forward command to the connected audio sender (e.g. mic script)
        # so it can start/stop capturing on its end too
        try:
            await self.send(text_data=json.dumps({"command": command}))
        except Exception:
            pass


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

            command = data.get("command")
            if command not in ("start", "stop"):
                return  # ignore unknown commands

            # Broadcast command to all AudioConsumers
            await self.channel_layer.group_send(
                AUDIO_GROUP,
                {"type": "control.command", "command": command}
            )

            # Also notify all other browser clients about the state change
            await self.channel_layer.group_send(
                BROWSER_GROUP,
                {"type": "status.update", "command": command}
            )

    async def audio_frame(self, event):
        await self.send(text_data=json.dumps({"audio": event["data"]}))

    async def status_update(self, event):
        """Broadcast start/stop state to all browser tabs."""
        await self.send(text_data=json.dumps({"status": event["command"]}))
