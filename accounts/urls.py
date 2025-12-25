from django.urls import path
from . import views

urlpatterns = [
    path("debattle/<slug:slug>/jury/", views.jury_view, name="debattle_jury"),
]