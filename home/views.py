from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from engine.services import openmuse_client


def _version() -> str:
    try:
        return (Path(settings.BASE_DIR) / "version.txt").read_text().strip()
    except OSError:
        return "?"


@require_GET
def index(request):
    """صفحهٔ اصلی: نسخهٔ زول و وضعیت موتور. فعلاً بدون ورود (تک‌کاربره)."""
    return render(
        request,
        "home/index.html",
        {"version": _version(), "engine": openmuse_client.health()},
    )


@require_GET
def health(request):
    """بررسی سلامت برای همروش (liveness). فقط خود جنگو؛ به موتور وابسته نیست."""
    return JsonResponse({"status": "ok", "version": _version()})
