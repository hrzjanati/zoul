from django.http import JsonResponse
from django.views.decorators.http import require_GET

from engine.services import openmuse_client


@require_GET
def engine_health(request):
    """وضعیت موتور به‌صورت JSON. همیشه ۲۰۰؛ وضعیت در بدنه است."""
    status = openmuse_client.health()
    return JsonResponse({"engine": "up" if status.reachable else "down", "detail": status.detail})
