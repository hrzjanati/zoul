from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from connectors.auth import require_engine_token
from connectors.services import google_oauth


# APIها با توکن Bearer محافظت می‌شوند، نه کوکی؛ پس CSRF موضوعیت ندارد.
@csrf_exempt
@require_POST
@require_engine_token
def google_start(request):
    try:
        return JsonResponse({"url": google_oauth.authorization_url()})
    except google_oauth.OAuthError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@require_GET
@require_engine_token
def google_status(request):
    return JsonResponse(google_oauth.status())


@csrf_exempt
@require_POST
@require_engine_token
def google_disconnect(request):
    return JsonResponse({"disconnected": google_oauth.disconnect()})


@require_GET
def google_callback(request):
    """گوگل بعد از «Allow» (یا «Cancel») به اینجا برمی‌گرداند. صفحهٔ ساده و دوزبانه."""
    ctx = {"ok": False, "email": "", "error": ""}
    if request.GET.get("error"):
        ctx["error"] = "اتصال لغو شد." if request.GET["error"] == "access_denied" else request.GET["error"]
        return render(request, "connectors/google_done.html", ctx, status=400)
    try:
        google_oauth.check_state(request.GET.get("state", ""))
        code = request.GET.get("code", "")
        if not code:
            raise google_oauth.OAuthError("گوگل کدی برنگرداند.")
        acc = google_oauth.exchange_code(code)
    except google_oauth.OAuthError as exc:
        ctx["error"] = str(exc)
        return render(request, "connectors/google_done.html", ctx, status=400)
    ctx.update(ok=True, email=acc.email)
    return render(request, "connectors/google_done.html", ctx)
