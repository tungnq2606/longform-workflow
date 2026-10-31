import importlib
import os
import shutil
import tempfile
import unittest
from unittest import mock

from tools.longform import inbox


class InboxTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.environ["LONGFORM_ROOT"] = self.root
        self.sent = []
        self.p = mock.patch.object(inbox.notify, "send", lambda t: self.sent.append(t) or True)
        self.p.start()

    def tearDown(self):
        self.p.stop()
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def test_add_and_list(self):
        inbox.add("001-a", "image_review", "BG08 3/5")
        second = inbox.add("001-a", "image_review", "BG09 3/5")
        items = inbox.open_items()
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["id"], second["id"])
        self.assertIn("http://127.0.0.1:8765/#/p/001-a", self.sent[0])

    def test_key_dedupes(self):
        inbox.add("001-a", "image_review", "BG08 3/5", key="img:BG08")
        inbox.add("001-a", "image_review", "BG08 vẫn 3/5", key="img:BG08")
        items = inbox.open_items()
        self.assertEqual([i["text"] for i in items], ["BG08 vẫn 3/5"])
        self.assertEqual(len(self.sent), 1)

    def test_resolve(self):
        it = inbox.add(None, "test", "x")
        self.assertTrue(inbox.resolve(it["id"]))
        self.assertEqual(inbox.open_items(), [])
        self.assertFalse(inbox.resolve("0" * 32))

    def test_resolve_key(self):
        inbox.add(None, "test", "x", key="k1")
        self.assertTrue(inbox.resolve_key("k1"))
        self.assertEqual(inbox.open_items(), [])

    def test_filter_project(self):
        inbox.add("001-a", "test", "a")
        inbox.add("002-b", "test", "b")
        self.assertEqual([i["text"] for i in inbox.open_items("002-b")], ["b"])

    def test_no_notify_flag(self):
        inbox.add(None, "test", "quiet", notify_owner=False)
        self.assertEqual(self.sent, [])

    def test_add_without_telegram(self):
        with mock.patch.object(inbox.notify, "send", lambda t: False):
            inbox.add(None, "test", "x")
        self.assertEqual(len(inbox.open_items()), 1)

    def test_survives_reload(self):
        inbox.add(None, "test", "x")
        importlib.reload(inbox)
        self.assertEqual(len(inbox.open_items()), 1)


if __name__ == "__main__":
    unittest.main()
