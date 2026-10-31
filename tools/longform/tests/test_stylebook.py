import os
import shutil
import tempfile
import unittest
from unittest import mock

WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class StylebookTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "library", "stylebook"))
        shutil.copy(os.path.join(WS, "library", "stylebook", "vi.json"), os.path.join(self.root, "library", "stylebook"))
        os.environ["LONGFORM_ROOT"] = self.root
        from tools.longform import inbox, stylebook
        self.sb, self.inbox = stylebook, inbox
        self.sent = []
        self.p = mock.patch.object(inbox.notify, "send", lambda t: self.sent.append(t) or True)
        self.p.start()

    def tearDown(self):
        self.p.stop()
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def test_seed_has_core_rules(self):
        kept = self.sb.kept("vi")
        self.assertTrue(any("chúng ta" in r and "bạn" in r for r in kept))
        self.assertTrue(any("tương truyền" in r for r in kept))
        self.assertGreaterEqual(len(kept), 10)
        self.assertTrue(all(os.path.isabs(p) for p in self.sb.load("vi")["examples"]))

    def test_propose_then_keep(self):
        r = self.sb.propose("vi", "Không dùng từ 'siêu'", "chat 001-a")
        self.assertEqual(r["status"], "proposed")
        self.assertNotIn("Không dùng từ 'siêu'", self.sb.kept("vi"))
        items = self.inbox.open_items()
        self.assertEqual([i["kind"] for i in items], ["style_rule"])
        self.assertEqual(self.sent, [])  # no Telegram for style rules
        self.sb.decide("vi", r["id"], True)
        self.assertIn("Không dùng từ 'siêu'", self.sb.kept("vi"))
        self.assertEqual(self.inbox.open_items(), [])

    def test_drop(self):
        r = self.sb.propose("vi", "Luôn mở bằng lời chào", "chat")
        self.sb.decide("vi", r["id"], False)
        self.assertNotIn("Luôn mở bằng lời chào", self.sb.kept("vi"))
        self.assertEqual([x["status"] for x in self.sb.load("vi")["rules"] if x["id"] == r["id"]], ["dropped"])

    def test_decide_unknown(self):
        with self.assertRaises(KeyError):
            self.sb.decide("vi", "R999", True)

    def test_each_lang_has_core_rules(self):
        legend = {"en": "legend says", "ja": "伝説によると", "de": "der Legende nach", "es": "según la leyenda"}
        for lang, word in legend.items():
            shutil.copy(os.path.join(WS, "library", "stylebook", "%s.json" % lang), os.path.join(self.root, "library", "stylebook"))
            kept = self.sb.kept(lang)
            self.assertGreaterEqual(len(kept), 10, lang)
            self.assertTrue(any(word in r for r in kept), lang)
            self.assertEqual(self.sb.load(lang)["lang"], lang)
        self.assertTrue(os.path.isfile(os.path.join(WS, "library", "localization", "GUIDE.md")))

    def test_missing_lang_empty(self):
        self.assertEqual(self.sb.load("ja"), {"lang": "ja", "rules": [], "examples": []})
        self.assertEqual(self.sb.kept("ja"), [])


if __name__ == "__main__":
    unittest.main()
