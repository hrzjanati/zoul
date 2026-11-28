"""
تست‌های اتصال گوگل. هیچ درخواست واقعی به گوگل نمی‌رود: همه با httpx.MockTransport.
"""
import base64
import json
from datetime import timedelta
from unittest import mock
from urllib.parse import parse_qs, urlparse

import httpx
from django.core import signing
from django.test import TestCase, override_settings
from django.utils import timezone

from connectors import mcp_google
from connectors.models import GoogleAccount
from connectors.services import crypto, google_api, google_oauth

TOKEN = "engine-token"
AUTH = {"HTTP_AUTHORIZATION": f"Bearer {TOKEN}"}
GOOGLE = dict(
    GOOGLE_OAUTH_CLIENT_ID="cid.apps.googleusercontent.com",
    GOOGLE_OAUTH_CLIENT_SECRET="GOCSPX-test",
    PUBLIC_URL="https://zoul.test",
    OPENMUSE_SERVER_TOKEN=TOKEN,
)


def google_transport(routes):
    """routes: {(METHOD, url-prefix): handler(request) -> httpx.Response | dict}"""
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        url = str(request.url)
        for (method, prefix), fn in routes.items():
            if request.method == method and url.startswith(prefix):
                out = fn(request)
                return out if isinstance(out, httpx.Response) else httpx.Response(200, json=out)
        return httpx.Response(404, json={"error": {"message": f"no route for {request.method} {url}"}})

    return httpx.MockTransport(handler), calls


def token_ok(_req):
    return {"access_token": "at-1", "expires_in": 3600, "refresh_token": "rt-1",
            "scope": " ".join(google_oauth.SCOPES)}


def make_account(**kw):
    acc = GoogleAccount(email="me@gmail.com", scopes=" ".join(google_oauth.SCOPES), **kw)
    acc.set_refresh_token("rt-1")
    acc.set_access_token("at-1", 3600)
    acc.save()
    return acc


class CryptoTests(TestCase):
    def test_roundtrip_and_tamper(self):
        enc = crypto.encrypt("secret")
        self.assertNotIn("secret", enc)
        self.assertEqual(crypto.decrypt(enc), "secret")
        self.assertIsNone(crypto.decrypt("not-a-token"))

    def test_other_secret_key_cannot_read(self):
        enc = crypto.encrypt("secret")
        with override_settings(SECRET_KEY="another-key"):
            self.assertIsNone(crypto.decrypt(enc))


@override_settings(**GOOGLE)
class EndpointAuthTests(TestCase):
    def test_start_needs_engine_token(self):
        self.assertEqual(self.client.post("/connectors/google/start").status_code, 401)
        self.assertEqual(self.client.post("/connectors/google/start", HTTP_AUTHORIZATION="Bearer wrong").status_code, 401)

    def test_status_and_disconnect_need_token(self):
        self.assertEqual(self.client.get("/connectors/google/status").status_code, 401)
        self.assertEqual(self.client.post("/connectors/google/disconnect").status_code, 401)

    @override_settings(OPENMUSE_SERVER_TOKEN="")
    def test_no_engine_token_configured_means_closed(self):
        self.assertEqual(self.client.post("/connectors/google/start", HTTP_AUTHORIZATION="Bearer ").status_code, 401)


@override_settings(**GOOGLE)
class OAuthFlowTests(TestCase):
    def test_start_returns_consent_url_with_all_products(self):
        resp = self.client.post("/connectors/google/start", **AUTH)
        self.assertEqual(resp.status_code, 200)
        url = urlparse(resp.json()["url"])
        q = parse_qs(url.query)
        self.assertEqual(url.netloc, "accounts.google.com")
        self.assertEqual(q["redirect_uri"], ["https://zoul.test/connectors/google/callback"])
        self.assertEqual(q["access_type"], ["offline"])
        for scope in google_oauth.PRODUCTS.values():
            self.assertIn(scope, q["scope"][0])
        google_oauth.check_state(q["state"][0])  # معتبر

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="")
    def test_start_without_client_says_so(self):
        resp = self.client.post("/connectors/google/start", **AUTH)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("GOOGLE_OAUTH_CLIENT_ID", resp.json()["error"])

    def test_callback_rejects_forged_or_old_state(self):
        resp = self.client.get("/connectors/google/callback", {"state": "forged", "code": "c"})
        self.assertEqual(resp.status_code, 400)
        old = signing.dumps({"n": "x"}, salt=google_oauth.STATE_SALT)
        with mock.patch("django.core.signing.time.time", return_value=__import__("time").time() + 3600):
            resp = self.client.get("/connectors/google/callback", {"state": old, "code": "c"})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(GoogleAccount.objects.exists())

    def test_callback_user_cancelled(self):
        resp = self.client.get("/connectors/google/callback", {"error": "access_denied"})
        self.assertEqual(resp.status_code, 400)
        self.assertContains(resp, "لغو", status_code=400)

    def test_callback_stores_encrypted_account(self):
        transport, calls = google_transport({
            ("POST", google_oauth.TOKEN_URL): token_ok,
            ("GET", google_oauth.USERINFO_URL): lambda r: {"email": "me@gmail.com", "name": "Hossein"},
        })
        state = signing.dumps({"n": "x"}, salt=google_oauth.STATE_SALT)
        real = google_oauth.exchange_code
        with mock.patch.object(google_oauth, "exchange_code", lambda code: real(code, transport=transport)):
            resp = self.client.get("/connectors/google/callback", {"state": state, "code": "the-code"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "me@gmail.com")
        acc = GoogleAccount.current()
        self.assertEqual(acc.email, "me@gmail.com")
        self.assertEqual(acc.refresh_token, "rt-1")
        self.assertNotIn("rt-1", acc.refresh_token_enc)  # رمزنگاری‌شده
        sent = parse_qs(calls[0].content.decode())
        self.assertEqual(sent["code"], ["the-code"])
        self.assertEqual(sent["client_secret"], ["GOCSPX-test"])

    def test_reconnect_replaces_old_account(self):
        make_account()
        transport, _ = google_transport({
            ("POST", google_oauth.TOKEN_URL): token_ok,
            ("GET", google_oauth.USERINFO_URL): lambda r: {"email": "other@gmail.com"},
        })
        google_oauth.exchange_code("c", transport=transport)
        self.assertEqual(list(GoogleAccount.objects.values_list("email", flat=True)), ["other@gmail.com"])

    def test_status(self):
        data = self.client.get("/connectors/google/status", **AUTH).json()
        self.assertTrue(data["configured"])
        self.assertFalse(data["connected"])
        make_account()
        data = self.client.get("/connectors/google/status", **AUTH).json()
        self.assertTrue(data["connected"])
        self.assertEqual(data["email"], "me@gmail.com")
        self.assertTrue(all(data["products"].values()))
        self.assertNotIn("rt-1", json.dumps(data))

    def test_disconnect_revokes_and_deletes(self):
        make_account()
        transport, calls = google_transport({("POST", google_oauth.REVOKE_URL): lambda r: {}})
        with mock.patch.object(google_oauth, "_client", lambda t=None: httpx.Client(transport=transport)):
            resp = self.client.post("/connectors/google/disconnect", **AUTH)
        self.assertEqual(resp.json(), {"disconnected": True})
        self.assertFalse(GoogleAccount.objects.exists())
        self.assertIn("token=rt-1", calls[0].content.decode())


@override_settings(**GOOGLE)
class GoogleApiTests(TestCase):
    def test_refreshes_expired_token(self):
        acc = make_account()
        acc.access_expires_at = timezone.now() - timedelta(minutes=1)
        acc.save()
        transport, calls = google_transport({
            ("POST", google_oauth.TOKEN_URL): lambda r: {"access_token": "at-2", "expires_in": 3600},
            ("GET", "https://example.googleapis.com/"): lambda r: {"auth": r.headers["Authorization"]},
        })
        with google_api.Google(transport=transport) as g:
            self.assertEqual(g.get("https://example.googleapis.com/x"), {"auth": "Bearer at-2"})

    def test_not_connected(self):
        with self.assertRaises(google_api.GoogleNotConnected):
            with google_api.Google() as g:
                g.get("https://example.googleapis.com/x")

    def test_revoked_access_says_reconnect(self):
        acc = make_account()
        acc.access_expires_at = timezone.now() - timedelta(minutes=1)
        acc.save()
        transport, _ = google_transport({
            ("POST", google_oauth.TOKEN_URL): lambda r: httpx.Response(400, json={"error": "invalid_grant"}),
        })
        with self.assertRaisesMessage(google_api.GoogleNotConnected, "Connect"):
            with google_api.Google(transport=transport) as g:
                g.get("https://example.googleapis.com/x")


@override_settings(**GOOGLE)
class McpToolTests(TestCase):
    """ابزارها با گوگل ساختگی؛ همان توابعی که سرور MCP صدا می‌زند."""

    def use(self, routes):
        transport, calls = google_transport(routes)
        patcher = mock.patch.object(mcp_google, "_session_factory", lambda: google_api.Google(transport=transport))
        patcher.start()
        self.addCleanup(patcher.stop)
        return calls

    def setUp(self):
        make_account()

    def test_tools_are_split_read_and_write(self):
        read = {f.__name__ for f in mcp_google.READ_TOOLS}
        write = {f.__name__ for f in mcp_google.WRITE_TOOLS}
        self.assertFalse(read & write)
        self.assertIn("gmail_send", write)
        self.assertIn("gmail_search", read)
        for fn in mcp_google.READ_TOOLS + mcp_google.WRITE_TOOLS:
            self.assertTrue(fn.__doc__, fn.__name__)

    def test_gmail_search_and_read(self):
        body = base64.urlsafe_b64encode("سلام، جلسه فردا ساعت ۱۰".encode()).decode().rstrip("=")
        self.use({
            ("GET", f"{mcp_google.GMAIL}/messages?"): lambda r: {"messages": [{"id": "m1"}]},
            ("GET", f"{mcp_google.GMAIL}/messages/m1"): lambda r: {
                "id": "m1", "threadId": "t1", "snippet": "سلام", "labelIds": ["UNREAD"],
                "payload": {"headers": [{"name": "From", "value": "Ali <ali@x.com>"}, {"name": "Subject", "value": "جلسه"}],
                            "mimeType": "multipart/alternative",
                            "parts": [{"mimeType": "text/plain", "body": {"data": body}}]},
            },
        })
        found = json.loads(mcp_google.gmail_search("from:ali"))
        self.assertEqual(found["messages"][0]["subject"], "جلسه")
        self.assertTrue(found["messages"][0]["unread"])
        msg = json.loads(mcp_google.gmail_read("m1"))
        self.assertIn("ساعت ۱۰", msg["body"])

    def test_gmail_send_builds_mime(self):
        calls = self.use({("POST", f"{mcp_google.GMAIL}/messages/send"): lambda r: {"id": "sent1"}})
        out = json.loads(mcp_google.gmail_send("a@b.com", "سلام", "متن"))
        self.assertEqual(out, {"sent": True, "id": "sent1"})
        raw = json.loads(calls[-1].content)["raw"]
        mime = base64.urlsafe_b64decode(raw + "==").decode()
        self.assertIn("To: a@b.com", mime)

    def test_drive_read_exports_google_doc(self):
        self.use({
            ("GET", f"{mcp_google.DRIVE}/files/d1/export"): lambda r: httpx.Response(200, text="متن سند"),
            ("GET", f"{mcp_google.DRIVE}/files/d1"): lambda r: {"id": "d1", "name": "یادداشت", "mimeType": "application/vnd.google-apps.document"},
        })
        out = json.loads(mcp_google.drive_read("d1"))
        self.assertEqual(out["text"], "متن سند")

    def test_drive_search_escapes_quotes(self):
        calls = self.use({("GET", f"{mcp_google.DRIVE}/files"): lambda r: {"files": []}})
        mcp_google.drive_search("ali's plan")
        q = parse_qs(urlparse(str(calls[-1].url)).query)["q"][0]
        self.assertIn("ali\\'s plan", q)
        self.assertIn("trashed = false", q)

    def test_sheets_read_and_append(self):
        calls = self.use({
            ("GET", f"{mcp_google.SHEETS}/s1/values/"): lambda r: {"range": "A1:B2", "values": [["نام", "مبلغ"], ["نان", "20"]]},
            ("POST", f"{mcp_google.SHEETS}/s1/values/"): lambda r: {"updates": {"updatedRows": 1}},
        })
        self.assertEqual(json.loads(mcp_google.sheets_read("s1", "A1:B2"))["values"][1], ["نان", "20"])
        self.assertEqual(json.loads(mcp_google.sheets_append("s1", [["شیر", "30"]])), {"updatedRows": 1})
        self.assertEqual(json.loads(calls[-1].content), {"values": [["شیر", "30"]]})

    def test_not_connected_is_a_readable_error(self):
        GoogleAccount.objects.all().delete()
        self.use({})
        self.assertTrue(mcp_google.calendar_events().startswith("ERROR: Google is not connected"))

    def test_api_error_is_reported(self):
        self.use({("GET", f"{mcp_google.TASKS}/"): lambda r: httpx.Response(403, json={"error": {"message": "API disabled"}})})
        self.assertIn("403", mcp_google.tasks_list())

    def test_build_server(self):
        self.assertEqual(mcp_google.build_server("read").name, "google")
        self.assertEqual(mcp_google.build_server("write").name, "google_write")
        with self.assertRaises(ValueError):
            mcp_google.build_server("x")
