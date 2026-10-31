import json
import os
import shutil
import tempfile
import unittest
from unittest import mock


class AudioLibTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.environ["LONGFORM_ROOT"] = self.root
        os.makedirs(os.path.join(self.root, "library", "audio"))
        with open(os.path.join(self.root, "library", "audio", "index.json"), "w") as f:
            json.dump({"music": [], "sfx": []}, f)
        with open(os.path.join(self.root, "LICENSES.md"), "w") as f:
            f.write("# Licences\n")
        from tools.longform import audio_lib, inbox
        self.a, self.inbox = audio_lib, inbox
        self.p = mock.patch.object(inbox.notify, "send", lambda t: True)
        self.p.start()
        self.src = os.path.join(self.root, "in")
        os.makedirs(self.src)

    def tearDown(self):
        self.p.stop()
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def file(self, name, data=b"ID3fake"):
        p = os.path.join(self.src, name)
        with open(p, "wb") as f:
            f.write(data)
        return p

    def test_add_requires_license(self):
        with self.assertRaisesRegex(ValueError, "giấy phép"):
            self.a.add(self.file("drum.mp3"), "music", "drums-01", "  ", mood="battle")
        with self.assertRaisesRegex(ValueError, "mp3"):
            self.a.add(self.file("drum.ogg"), "music", "drums-01", "CC0 https://x", mood="battle")
        with self.assertRaisesRegex(ValueError, "mood"):
            self.a.add(self.file("drum.mp3"), "music", "drums-01", "CC0 https://x", mood="happy")
        self.assertEqual(self.a.load(), {"music": [], "sfx": []})

    def test_add_copies_and_logs_license(self):
        e = self.a.add(self.file("sw.wav"), "sfx", "sword-01", "Pixabay licence https://pixabay.com/x", tags=["sword"])
        self.assertEqual(e["file"], "sfx/sword-01.wav")
        self.assertTrue(os.path.isfile(os.path.join(self.root, "library", "audio", "sfx", "sword-01.wav")))
        self.assertEqual(self.a.load()["sfx"][0]["license"], "Pixabay licence https://pixabay.com/x")
        with open(os.path.join(self.root, "LICENSES.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("sword-01", text)
        self.assertIn("Pixabay licence https://pixabay.com/x", text)
        with self.assertRaisesRegex(ValueError, "trùng"):
            self.a.add(self.file("sw2.wav"), "sfx", "sword-01", "x", tags=["sword"])

    def test_problems_missing_file(self):
        self.a.add(self.file("m.mp3"), "music", "open-01", "CC-BY 4.0 https://x", mood="opening")
        os.remove(os.path.join(self.root, "library", "audio", "music", "open-01.mp3"))
        idx = self.a.load()
        idx["sfx"].append({"id": "wind-01", "file": "sfx/wind-01.mp3", "kind": "sfx", "tags": ["wind"], "license": ""})
        with open(os.path.join(self.root, "library", "audio", "index.json"), "w") as f:
            json.dump(idx, f)
        os.makedirs(os.path.join(self.root, "library", "audio", "sfx"), exist_ok=True)
        open(os.path.join(self.root, "library", "audio", "sfx", "wind-01.mp3"), "wb").close()
        probs = self.a.problems()
        self.assertTrue(any("open-01" in p and "thiếu file" in p for p in probs))
        self.assertTrue(any("wind-01" in p and "giấy phép" in p for p in probs))

    def test_by_mood_and_tag(self):
        self.a.add(self.file("a.mp3"), "music", "battle-01", "L", mood="battle")
        self.a.add(self.file("b.mp3"), "music", "end-01", "L", mood="ending")
        self.a.add(self.file("c.mp3"), "sfx", "oar-01", "L", tags=["oar", "water"])
        self.assertEqual([e["id"] for e in self.a.by_mood("battle")], ["battle-01"])
        self.assertEqual([e["id"] for e in self.a.by_tag("water")], ["oar-01"])
        self.assertEqual(self.a.ids(), {"battle-01", "end-01", "oar-01"})

    def test_empty_library_inbox_once(self):
        self.a.warn_if_empty("001-a")
        self.a.warn_if_empty("001-a")
        items = [i for i in self.inbox.open_items() if i["kind"] == "audio_missing"]
        self.assertEqual(len(items), 1)
        self.assertIn("Thư viện nhạc/hiệu ứng trống", items[0]["text"])
        self.a.add(self.file("a.mp3"), "music", "battle-01", "L", mood="battle")
        self.assertFalse([i for i in self.inbox.open_items() if i["kind"] == "audio_missing"])


if __name__ == "__main__":
    unittest.main()
