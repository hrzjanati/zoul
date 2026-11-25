from unittest import mock

import httpx
from django.test import SimpleTestCase
from django.urls import reverse


class HomeTests(SimpleTestCase):
    def test_health_does_not_touch_engine(self):
        with mock.patch("httpx.get") as get:
            resp = self.client.get(reverse("home:health"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")
        get.assert_not_called()

    def test_index_renders_when_engine_down(self):
        with mock.patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            resp = self.client.get(reverse("home:index"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "موتور در دسترس نیست")

    def test_index_lives_under_zoul_not_root(self):
        # ریشه مال UI موتور است (nginx)؛ جنگو نباید روی / چیزی داشته باشد.
        self.assertEqual(reverse("home:index"), "/zoul/")
        self.assertEqual(self.client.get("/").status_code, 404)
