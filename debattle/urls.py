from django.urls import path
from . import views

urlpatterns = [
    path("", views.index_view, name="index"),

    path("debattle/<slug:slug>/screen/", views.screen_view, name="debattle_screen"),
    path("debattle/<slug:slug>/control/", views.control_view, name="debattle_control"),
    path("debattle/<slug:slug>/register/", views.register_team_view, name="debattle_register"),
]