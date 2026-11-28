from django.contrib import admin

from connectors.models import GoogleAccount


@admin.register(GoogleAccount)
class GoogleAccountAdmin(admin.ModelAdmin):
    list_display = ("email", "connected_at", "last_used_at")
    # توکن‌ها هرگز در ادمین نشان داده نمی‌شوند.
    exclude = ("refresh_token_enc", "access_token_enc")
    readonly_fields = ("email", "name", "scopes", "access_expires_at", "connected_at", "last_used_at")

    def has_add_permission(self, request):
        return False  # فقط از راه دکمهٔ «اتصال» در زول
