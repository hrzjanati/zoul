from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("engine/", include("engine.urls")),
    path("connectors/", include("connectors.urls")),
    path("", include("home.urls")),
]
