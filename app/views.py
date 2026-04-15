import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

AUDIO_GROUP = "live_audio"

@csrf_exempt
def control(request):
    if request.method == "POST":
        data = json.loads(request.body)
        command = data.get("command")  # "start" or "stop"
        if command not in ("start", "stop"):
            return JsonResponse({"error": "invalid command"}, status=400)

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            AUDIO_GROUP,
            {"type": "control.command", "command": command}
        )
        return JsonResponse({"status": "ok", "command": command})

    return JsonResponse({"error": "POST required"}, status=405)


def index(request):
    from django.shortcuts import render
    return render(request, "index.html")