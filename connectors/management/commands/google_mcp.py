"""
سرور MCP گوگل روی stdio. موتور OpenMuse خودش اجرایش می‌کند (engine/openmuse/config.toml):

    python /code/manage.py google_mcp --mode read
    python /code/manage.py google_mcp --mode write

⚠️ stdout مال پروتکل MCP است؛ هیچ چیزی نباید روی آن چاپ شود. لاگ‌ها به stderr.
"""
import anyio
from django.core.management.base import BaseCommand

from connectors.mcp_google import build_server


class Command(BaseCommand):
    help = "Run the Google MCP server (read or write tools) over stdio."

    def add_arguments(self, parser):
        parser.add_argument("--mode", choices=["read", "write"], required=True)

    def handle(self, *args, mode: str, **options):
        server = build_server(mode)
        anyio.run(server.run_stdio_async)
