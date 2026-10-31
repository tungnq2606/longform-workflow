import os
import unittest
from unittest import mock

from tools import notify


class NotifyTest(unittest.TestCase):
    def test_conf_path(self):
        self.assertTrue(notify.CONF.endswith(os.path.join("config", "secrets", "telegram.json")))

    def test_link_project(self):
        self.assertEqual(notify.link("001-bach-dang", "images"), "http://127.0.0.1:8765/#/p/001-bach-dang/images")

    def test_link_project_no_screen(self):
        self.assertEqual(notify.link("001-bach-dang"), "http://127.0.0.1:8765/#/p/001-bach-dang")

    def test_link_home(self):
        self.assertEqual(notify.link(None), "http://127.0.0.1:8765/#/")

    def test_send_without_secret(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("TELEGRAM_")}
        with mock.patch.object(notify, "CONF", "/nonexistent/telegram.json"), mock.patch.dict(os.environ, env, clear=True):
            self.assertIs(notify.send("x"), False)


if __name__ == "__main__":
    unittest.main()
