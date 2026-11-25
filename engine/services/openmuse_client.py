"""
تنها درگاه جنگو به موتور OpenMuse.

مثل robots/services/family_bridge.py در «خانواده من»: هیچ فایل دیگری در
پروژه مستقیم به API موتور درخواست نمی‌فرستد. اگر روزی موتور عوض شود
(نسخهٔ جدید OpenMuse یا موتوری دیگر)، فقط همین فایل تغییر می‌کند.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx
from django.conf import settings


@dataclass(frozen=True)
class EngineStatus:
    reachable: bool
    detail: str = ""
    data: dict | None = None


def _headers() -> dict[str, str]:
    token = settings.OPENMUSE_SERVER_TOKEN
    return {"Authorization": f"Bearer {token}"} if token else {}


def health() -> EngineStatus:
    """آیا موتور بالا است؟ (/api/health نیازی به توکن ندارد.)

    هیچ‌وقت استثنا بیرون نمی‌دهد: پایین بودن موتور نباید صفحهٔ وب را بخواباند.
    """
    url = f"{settings.OPENMUSE_URL}/api/health"
    try:
        resp = httpx.get(url, timeout=settings.OPENMUSE_TIMEOUT)
    except httpx.HTTPError as exc:
        return EngineStatus(reachable=False, detail=type(exc).__name__)
    if resp.status_code != 200:
        return EngineStatus(reachable=False, detail=f"HTTP {resp.status_code}")
    try:
        data = resp.json()
    except ValueError:
        data = None
    return EngineStatus(reachable=True, data=data if isinstance(data, dict) else None)
