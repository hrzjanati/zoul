from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("engine/", include("engine.urls")),
    path("", include("home.urls")),
]
