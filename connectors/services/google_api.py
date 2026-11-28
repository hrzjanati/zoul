"""
فراخوانی APIهای گوگل با توکنِ حسابِ وصل‌شده.

فقط همین فایل با googleapis.com حرف می‌زند (مثل openmuse_client برای موتور).
توکن دسترسی خودکار تازه می‌شود؛ اگر حسابی وصل نباشد یا گوگل اتصال را رد کند،
`GoogleNotConnected` با پیامی برای کاربر بالا می‌رود.
"""
from __future__ import annotations

from typing import Any

import httpx
from django.utils import timezone

from connectors.models import GoogleAccount
from connectors.services import google_oauth


class GoogleNotConnected(Exception):
    pass


class GoogleAPIError(Exception):
    pass


NOT_CONNECTED = (
    "Google is not connected. Ask the user to open Zoul → Connections → Google and press Connect. "
    "(گوگل وصل نیست؛ در زول به «اتصال‌ها ← گوگل» برو و «اتصال» را بزن.)"
)


class Google:
    """یک جلسه برای چند درخواست. `transport` فقط برای تست."""

    def __init__(self, transport: httpx.BaseTransport | None = None):
        self._transport = transport
        self._http = httpx.Client(timeout=40, transport=transport)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "Google":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ---------- توکن ----------
    def _token(self, force_refresh: bool = False) -> str:
        acc = GoogleAccount.current()
        if acc is None:
            raise GoogleNotConnected(NOT_CONNECTED)
        token = None if force_refresh else acc.access_token
        if not token:
            try:
                token = google_oauth.refresh_access_token(acc, transport=self._transport)
            except google_oauth.OAuthError as exc:
                raise GoogleNotConnected(f"{exc} {NOT_CONNECTED}") from exc
        GoogleAccount.objects.filter(pk=acc.pk).update(last_used_at=timezone.now())
        return token

    def request(self, method: str, url: str, *, raw: bool = False, **kwargs: Any) -> Any:
        resp = self._send(method, url, self._token(), **kwargs)
        if resp.status_code == 401:  # توکن وسط کار باطل شده
            resp = self._send(method, url, self._token(force_refresh=True), **kwargs)
        if resp.status_code >= 400:
            try:
                msg = resp.json().get("error", {})
                msg = msg.get("message", msg) if isinstance(msg, dict) else msg
            except ValueError:
                msg = resp.text[:300]
            raise GoogleAPIError(f"Google API error {resp.status_code}: {msg}")
        if raw:
            return resp
        if not resp.content:
            return {}
        return resp.json()

    def _send(self, method: str, url: str, token: str, **kwargs: Any) -> httpx.Response:
        headers = {**kwargs.pop("headers", {}), "Authorization": f"Bearer {token}"}
        return self._http.request(method, url, headers=headers, **kwargs)

    def get(self, url: str, **kw: Any) -> Any:
        return self.request("GET", url, **kw)

    def post(self, url: str, **kw: Any) -> Any:
        return self.request("POST", url, **kw)

    def put(self, url: str, **kw: Any) -> Any:
        return self.request("PUT", url, **kw)

    def patch(self, url: str, **kw: Any) -> Any:
        return self.request("PATCH", url, **kw)
