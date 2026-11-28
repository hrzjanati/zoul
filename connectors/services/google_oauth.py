"""
اتصال یک‌کلیکی به گوگل (OAuth 2.0، Web application).

جریان:
  ۱. UI با توکن زول POST /connectors/google/start می‌زند ← لینک صفحهٔ اجازهٔ گوگل
     با یک `state` امضاشده و ده‌دقیقه‌ای.
  ۲. کاربر در گوگل «Allow» می‌زند ← گوگل به /connectors/google/callback برمی‌گرداند.
  ۳. state چک می‌شود، code با Client Secret به توکن تبدیل می‌شود، refresh token
     رمزنگاری‌شده ذخیره می‌شود.
چون شروع جریان توکن زول می‌خواهد، کسی بیرون از زول نمی‌تواند state معتبر بسازد و
حساب گوگل خودش را به ایجنت تو وصل کند.

مستند: docs/features/google.md
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from django.conf import settings
from django.core import signing
from django.db import transaction

from connectors.models import GoogleAccount

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

# همهٔ محصولات با یک کلیک. نوشتن‌ها را Sentinel همیشه با تأیید اجرا می‌کند.
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/tasks",
]

# برای UI: هر محصول کدام مجوز را لازم دارد.
PRODUCTS = {
    "gmail": "https://www.googleapis.com/auth/gmail.modify",
    "drive": "https://www.googleapis.com/auth/drive",
    "sheets": "https://www.googleapis.com/auth/spreadsheets",
    "docs": "https://www.googleapis.com/auth/documents",
    "calendar": "https://www.googleapis.com/auth/calendar",
    "contacts": "https://www.googleapis.com/auth/contacts.readonly",
    "tasks": "https://www.googleapis.com/auth/tasks",
}

STATE_SALT = "zoul.connectors.google.state"
STATE_MAX_AGE = 600


class OAuthError(Exception):
    """خطایی که پیامش برای کاربر نشان داده می‌شود."""


@dataclass(frozen=True)
class Config:
    client_id: str
    client_secret: str
    redirect_uri: str


def config() -> Config | None:
    cid = settings.GOOGLE_OAUTH_CLIENT_ID
    secret = settings.GOOGLE_OAUTH_CLIENT_SECRET
    if not cid or not secret:
        return None
    return Config(cid, secret, settings.PUBLIC_URL + "/connectors/google/callback")


def _client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(timeout=20, transport=transport)


def authorization_url() -> str:
    cfg = config()
    if cfg is None:
        raise OAuthError("اتصال گوگل تنظیم نشده: GOOGLE_OAUTH_CLIENT_ID و GOOGLE_OAUTH_CLIENT_SECRET لازم‌اند.")
    state = signing.dumps({"n": secrets.token_urlsafe(16)}, salt=STATE_SALT)
    params = {
        "client_id": cfg.client_id,
        "redirect_uri": cfg.redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        # offline + consent: تا refresh token حتماً برگردد (حتی در اتصال دوباره).
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def check_state(state: str) -> None:
    try:
        signing.loads(state, salt=STATE_SALT, max_age=STATE_MAX_AGE)
    except signing.SignatureExpired as exc:
        raise OAuthError("لینک اتصال منقضی شده؛ دوباره از زول «اتصال» را بزن.") from exc
    except signing.BadSignature as exc:
        raise OAuthError("درخواست اتصال معتبر نیست؛ دوباره از زول «اتصال» را بزن.") from exc


def exchange_code(code: str, transport: httpx.BaseTransport | None = None) -> GoogleAccount:
    """code را به توکن تبدیل می‌کند و حساب را ذخیره می‌کند (جای حساب قبلی)."""
    cfg = config()
    if cfg is None:
        raise OAuthError("اتصال گوگل تنظیم نشده.")
    with _client(transport) as http:
        resp = http.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": cfg.client_id,
                "client_secret": cfg.client_secret,
                "redirect_uri": cfg.redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if resp.status_code != 200:
            raise OAuthError(f"گوگل توکن نداد (HTTP {resp.status_code}).")
        tok = resp.json()
        refresh = tok.get("refresh_token")
        if not refresh:
            raise OAuthError("گوگل refresh token نداد؛ دوباره «اتصال» را بزن.")
        info = http.get(USERINFO_URL, headers={"Authorization": f"Bearer {tok['access_token']}"})
        info = info.json() if info.status_code == 200 else {}

    with transaction.atomic():
        GoogleAccount.objects.all().delete()
        acc = GoogleAccount(
            email=info.get("email", ""),
            name=info.get("name", ""),
            scopes=tok.get("scope", ""),
        )
        acc.set_refresh_token(refresh)
        acc.set_access_token(tok["access_token"], tok.get("expires_in", 3600))
        acc.save()
    return acc


def refresh_access_token(acc: GoogleAccount, transport: httpx.BaseTransport | None = None) -> str:
    cfg = config()
    refresh = acc.refresh_token
    if cfg is None or not refresh:
        raise OAuthError("اتصال گوگل معتبر نیست؛ در زول دوباره «اتصال» را بزن.")
    with _client(transport) as http:
        resp = http.post(
            TOKEN_URL,
            data={
                "client_id": cfg.client_id,
                "client_secret": cfg.client_secret,
                "refresh_token": refresh,
                "grant_type": "refresh_token",
            },
        )
    if resp.status_code != 200:
        # invalid_grant: کاربر دسترسی را در حساب گوگل پس گرفته یا توکن منقضی شده.
        raise OAuthError("گوگل اتصال را رد کرد (شاید دسترسی پس گرفته شده)؛ در زول دوباره «اتصال» را بزن.")
    tok = resp.json()
    acc.set_access_token(tok["access_token"], tok.get("expires_in", 3600))
    acc.save(update_fields=["access_token_enc", "access_expires_at"])
    return tok["access_token"]


def disconnect(transport: httpx.BaseTransport | None = None) -> bool:
    """توکن را در گوگل باطل و از دیتابیس پاک می‌کند. True اگر حسابی وصل بود."""
    acc = GoogleAccount.current()
    if acc is None:
        return False
    refresh = acc.refresh_token
    if refresh:
        try:
            with _client(transport) as http:
                http.post(REVOKE_URL, data={"token": refresh})
        except httpx.HTTPError:
            pass  # پاک کردن محلی مهم‌تر است؛ کاربر می‌تواند از حساب گوگل هم پس بگیرد.
    GoogleAccount.objects.all().delete()
    return True


def status() -> dict:
    acc = GoogleAccount.current()
    granted = set(acc.scope_list) if acc else set()
    return {
        "configured": config() is not None,
        "connected": acc is not None,
        "email": acc.email if acc else "",
        "name": acc.name if acc else "",
        "connected_at": acc.connected_at.isoformat() if acc else None,
        "products": {k: (v in granted) for k, v in PRODUCTS.items()},
        "redirect_uri": settings.PUBLIC_URL + "/connectors/google/callback",
    }
