"""
دسترسی به APIهای اتصال: فقط با همان توکن زول (OPENMUSE_SERVER_TOKEN).

فعلاً زول ورود کاربر ندارد؛ هر کس این توکن را داشته باشد صاحب زول است. UI همان
توکنی را که برای موتور دارد در هدر `Authorization: Bearer ...` می‌فرستد.
"""
from __future__ import annotations

import secrets
from functools import wraps

from django.conf import settings
from django.http import JsonResponse


def _bearer(request) -> str:
    header = request.headers.get("Authorization", "")
    return header[7:].strip() if header.lower().startswith("bearer ") else ""


def require_engine_token(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        expected = settings.OPENMUSE_SERVER_TOKEN
        given = _bearer(request)
        if not expected or not given or not secrets.compare_digest(given.encode(), expected.encode()):
            return JsonResponse({"error": "unauthorized"}, status=401)
        return view(request, *args, **kwargs)

    return wrapper
