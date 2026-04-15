from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
re_path(r"ws/audio/?$", consumers.AudioConsumer.as_asgi()),
    re_path(r"ws/browser/$", consumers.BrowserConsumer.as_asgi()),
]