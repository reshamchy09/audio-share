import json
from channels.generic.websocket import AsyncWebsocketConsumer

# Group name shared by device and browser
AUDIO_GROUP = "live_audio"

class AudioConsumer(AsyncWebsocketConsumer):
    """Receives raw PCM bytes from Android and forwards to all browsers."""

    async def connect(self):
        await self.channel_layer.group_add(AUDIO_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(AUDIO_GROUP, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data:
            # Broadcast raw PCM to all browser listeners
            await self.channel_layer.group_send(
                AUDIO_GROUP,
                {"type": "audio.frame", "data": bytes_data.hex()}
            )

    async def audio_frame(self, event):
        # Not sent back to Android
        pass

    async def control_command(self, event):
        """Relay start/stop command to Android device."""
        await self.send(text_data=json.dumps({"command": event["command"]}))


class BrowserConsumer(AsyncWebsocketConsumer):
    """Sends audio frames to the browser and forwards control commands."""

    async def connect(self):
        await self.channel_layer.group_add(AUDIO_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(AUDIO_GROUP, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass  # Browser doesn't send audio

    async def audio_frame(self, event):
        """Forward PCM frame to browser as hex string."""
        await self.send(text_data=json.dumps({"audio": event["data"]}))


# HTTP view to send start/stop command to Android