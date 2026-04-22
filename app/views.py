import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

AUDIO_GROUP = "live_audio"


def login_view(request):
    error = ""

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        if username == "admin" and password == "pooja":
            return redirect("index")
        else:
            error = "Invalid username or password"

    return render(request, "login.html", {"error": error})


def index(request):
    return render(request, "index.html")


@csrf_exempt
def control(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            command = data.get("command")

            if command not in ("start", "stop"):
                return JsonResponse({"error": "invalid command"}, status=400)

            channel_layer = get_channel_layer()

            async_to_sync(channel_layer.group_send)(
                AUDIO_GROUP,
                {
                    "type": "control.command",
                    "command": command
                }
            )

            return JsonResponse({"status": "ok", "command": command})

        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid json"}, status=400)

    return JsonResponse({"error": "POST required"}, status=405)
