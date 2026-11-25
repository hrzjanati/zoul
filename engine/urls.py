from django.urls import path

from engine import views

app_name = "engine"

urlpatterns = [
    path("health/", views.engine_health, name="health"),
]
