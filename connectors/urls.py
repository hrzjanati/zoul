from django.urls import path

from connectors import views

app_name = "connectors"

urlpatterns = [
    path("google/start", views.google_start, name="google_start"),
    path("google/status", views.google_status, name="google_status"),
    path("google/disconnect", views.google_disconnect, name="google_disconnect"),
    path("google/callback", views.google_callback, name="google_callback"),
]
