import json
import asyncio
import subprocess
import base64
from channels.generic.websocket import AsyncWebsocketConsumer

AUDIO_GROUP = "live_audio"
BROWSER_GROUP = "live_browser"


class AudioConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(AUDIO_GROUP, self.channel_name)
        await self.accept()

        self.is_streaming = False

        # 🎯 Start FFmpeg process (PCM → MP3)
        self.ffmpeg = subprocess.Popen(
            [
                "ffmpeg",
                "-f", "s16le",          # PCM 16-bit little-endian
                "-ar", "44100",         # sample rate
                "-ac", "1",             # mono audio
                "-i", "pipe:0",         # input from stdin
                "-f", "mp3",
                "-b:a", "128k",         # bitrate
                "pipe:1"                # output to stdout
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        self.keepalive_task = asyncio.create_task(self.send_keepalive())
        self.read_task = asyncio.create_task(self.read_mp3_stream())

    async def disconnect(self, code):
        self.keepalive_task.cancel()
        self.read_task.cancel()

        if self.ffmpeg:
            self.ffmpeg.terminate()

        await self.channel_layer.group_discard(AUDIO_GROUP, self.channel_name)

    async def send_keepalive(self):
        while True:
            await asyncio.sleep(30)
            try:
                await self.send(text_data=json.dumps({"type": "ping"}))
            except Exception:
                break

    async def read_mp3_stream(self):
        """Read encoded MP3 from FFmpeg and broadcast"""
        while True:
            if self.ffmpeg.stdout:
                data = await asyncio.get_event_loop().run_in_executor(
                    None, self.ffmpeg.stdout.read, 1024
                )

                if data:
                    mp3_base64 = base64.b64encode(data).decode()

                    await self.channel_layer.group_send(
                        BROWSER_GROUP,
                        {
                            "type": "audio.frame",
                            "data": mp3_base64
                        }
                    )

            await asyncio.sleep(0.01)

    async def receive(self, text_data=None, bytes_data=None):

        if text_data:
            data = json.loads(text_data)

            if data.get("type") == "pong":
                return

        # 🎯 PCM audio coming from Android / mic client
        if bytes_data and self.is_streaming:

            try:
                self.ffmpeg.stdin.write(bytes_data)
                self.ffmpeg.stdin.flush()
            except Exception:
                pass

    async def audio_frame(self, event):
        pass

    async def control_command(self, event):
        command = event.get("command")

        if command == "start":
            self.is_streaming = True
        elif command == "stop":
            self.is_streaming = False

        await self.send(text_data=json.dumps({"command": command}))


class BrowserConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(BROWSER_GROUP, self.channel_name)
        await self.accept()

        self.keepalive_task = asyncio.create_task(self.send_keepalive())

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
                return

            command = data.get("command")
            if command not in ("start", "stop"):
                return

            await self.channel_layer.group_send(
                AUDIO_GROUP,
                {
                    "type": "control.command",
                    "command": command
                }
            )

            await self.channel_layer.group_send(
                BROWSER_GROUP,
                {
                    "type": "status.update",
                    "command": command
                }
            )

    async def audio_frame(self, event):
        # 🎧 Receive MP3 base64
        await self.send(text_data=json.dumps({
            "audio_mp3": event["data"]
        }))

    async def status_update(self, event):
        await self.send(text_data=json.dumps({
            "status": event["command"]
        }))
