from datetime import timedelta

from django.db import models
from django.utils import timezone

from connectors.services import crypto


class GoogleAccount(models.Model):
    """حساب گوگلِ وصل‌شده. فعلاً تک‌کاربره: حداکثر یک ردیف.

    refresh token رمزنگاری‌شده ذخیره می‌شود و هرگز به مدل یا UI نمی‌رسد.
    """

    email = models.EmailField("ایمیل")
    name = models.CharField("نام", max_length=200, blank=True)
    scopes = models.TextField("مجوزها", blank=True, help_text="با فاصله جدا شده")
    refresh_token_enc = models.TextField()
    access_token_enc = models.TextField(blank=True)
    access_expires_at = models.DateTimeField(null=True, blank=True)
    connected_at = models.DateTimeField("زمان اتصال", default=timezone.now)
    last_used_at = models.DateTimeField("آخرین استفاده", null=True, blank=True)

    class Meta:
        verbose_name = "حساب گوگل"
        verbose_name_plural = "حساب‌های گوگل"

    def __str__(self) -> str:
        return self.email

    # ---------- توکن‌ها ----------
    @property
    def refresh_token(self) -> str | None:
        return crypto.decrypt(self.refresh_token_enc)

    def set_refresh_token(self, token: str) -> None:
        self.refresh_token_enc = crypto.encrypt(token)

    @property
    def access_token(self) -> str | None:
        if not self.access_token_enc or not self.access_expires_at:
            return None
        # یک دقیقه حاشیه، تا توکن وسط درخواست منقضی نشود.
        if self.access_expires_at <= timezone.now() + timedelta(seconds=60):
            return None
        return crypto.decrypt(self.access_token_enc)

    def set_access_token(self, token: str, expires_in: int) -> None:
        self.access_token_enc = crypto.encrypt(token)
        self.access_expires_at = timezone.now() + timedelta(seconds=int(expires_in))

    @property
    def scope_list(self) -> list[str]:
        return self.scopes.split()

    @classmethod
    def current(cls) -> "GoogleAccount | None":
        return cls.objects.order_by("-connected_at").first()
