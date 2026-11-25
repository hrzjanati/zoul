from unittest import mock

import httpx
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from engine.services import openmuse_client


@override_settings(OPENMUSE_URL="http://engine.test")
class OpenMuseClientTests(SimpleTestCase):
    def test_engine_down_never_raises(self):
        with mock.patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            status = openmuse_client.health()
        self.assertFalse(status.reachable)
        self.assertEqual(status.detail, "ConnectError")

    def test_engine_up(self):
        resp = httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", "http://engine.test"))
        with mock.patch("httpx.get", return_value=resp) as get:
            status = openmuse_client.health()
        self.assertTrue(status.reachable)
        get.assert_called_once()
        self.assertEqual(get.call_args.args[0], "http://engine.test/api/health")

    def test_non_200_is_down(self):
        resp = httpx.Response(503, request=httpx.Request("GET", "http://engine.test"))
        with mock.patch("httpx.get", return_value=resp):
            status = openmuse_client.health()
        self.assertFalse(status.reachable)
        self.assertEqual(status.detail, "HTTP 503")


class EngineHealthViewTests(SimpleTestCase):
    def test_reports_down_with_200(self):
        with mock.patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            resp = self.client.get(reverse("engine:health"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["engine"], "down")
