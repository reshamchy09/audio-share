from django.urls import path
from . import views

urlpatterns = [
       path("", login_view, name="login"),
    path("index",          views.index,   name="index"),
    path("control/",  views.control, name="control"),
]
