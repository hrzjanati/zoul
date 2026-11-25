from django.urls import path

from home import views

app_name = "home"

# ریشهٔ دامنه (/) مال UI موتور است (deploy/nginx.conf)؛ صفحهٔ جنگو زیر /zoul/.
urlpatterns = [
    path("zoul/", views.index, name="index"),
    path("health/", views.health, name="health"),
]
