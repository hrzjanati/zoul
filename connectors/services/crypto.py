"""
رمزنگاری توکن‌های اتصال‌ها (Fernet).

کلید از SECRET_KEY جنگو مشتق می‌شود، پس متغیر محیطی تازه‌ای لازم نیست.
⚠️ اگر SECRET_KEY عوض شود، توکن‌های ذخیره‌شده دیگر باز نمی‌شوند و باید
دوباره «اتصال» زد — هیچ داده‌ای از گوگل از دست نمی‌رود.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

_SALT = b"zoul.connectors.v1"


def _fernet() -> Fernet:
    digest = hashlib.sha256(_SALT + settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str | None:
    """None اگر با کلید فعلی باز نشود (SECRET_KEY عوض شده)."""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return None
