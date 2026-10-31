"""Voice parts per tool limits (Vbee ~55 s, ElevenLabs 4,500 characters) and the owner's mp3 drop-in."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MP3 = b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\x00" * 64


def doc(texts, lang="vi"):
    return {"lang": lang, "chapters": [{"id": "C01", "title": "T", "beats": [{"id": "B01", "goal": "g", "sentences": [
        {"id": "s%03d" % (i + 1), "text": t, "facts": [], "kind": "narration", "note": ""} for i, t in enumerate(texts)]}]}]}


class VoiceTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "config"))
        for f in ("languages.json", "studio.json"):
            shutil.copy(os.path.join(WS, "config", f), os.path.join(self.root, "config"))
        os.environ["LONGFORM_ROOT"] = self.root
        from tools.longform import inbox, jobs, languages, progress, project, script, voice
        self.inbox, self.jobs, self.langs, self.progress, self.script, self.v = inbox, jobs, languages, progress, script, voice
        self.p = mock.patch.object(inbox.notify, "send", lambda t: True)
        self.p.start()
        self.kinds = dict(jobs.KINDS)
        jobs.register(jobs.Kind("timing_build", "cpu", lambda params: [sys.executable, "-c", "print(1)"]))  # Plan 5 owns it
        self.pdir = project.create_project(1, "a", "A", ["en"])

    def tearDown(self):
        self.p.stop()
        self.jobs.KINDS.clear()
        self.jobs.KINDS.update(self.kinds)
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def cfg(self, code):
        return self.langs.load_languages()[code]

    def approved(self, texts):
        self.script.save(self.pdir, doc(texts), "owner")
        self.script.approve(self.pdir, "owner")

    def test_split_respects_seconds(self):
        vi = self.cfg("vi")
        self.assertEqual((vi.chars_per_second, vi.max_part_seconds, vi.max_part_chars), (15.5, 55, None))
        sents = [("s%03d" % i, "x" * 300) for i in range(1, 8)]  # 300 chars = 19.4 s each
        parts = self.v.split(sents, vi)
        self.assertEqual([p["part"] for p in parts], ["01", "02", "03", "04"])
        self.assertEqual([p["sentences"] for p in parts][0], ["s001", "s002"])
        self.assertTrue(all(p["seconds"] <= 55 for p in parts))
        self.assertEqual(sum(len(p["sentences"]) for p in parts), 7)
        self.assertTrue(all(p["flags"] == [] for p in parts))

    def test_split_respects_chars(self):
        en = self.cfg("en")
        self.assertEqual((en.max_part_seconds, en.max_part_chars), (None, 4500))
        sents = [("s%03d" % i, "y" * 1000) for i in range(1, 11)]
        parts = self.v.split(sents, en)
        self.assertTrue(all(len(p["text"]) <= 4500 for p in parts))
        self.assertEqual([len(p["sentences"]) for p in parts], [4, 4, 2])
        self.assertEqual(parts[0]["text"].split("\n"), ["y" * 1000] * 4)

    def test_long_sentence_own_part_flagged(self):
        vi = self.cfg("vi")
        sents = [("s001", "a" * 100), ("s002", "b" * 1000), ("s003", "c" * 100)]  # s002 = 64.5 s
        parts = self.v.split(sents, vi)
        self.assertEqual([p["sentences"] for p in parts], [["s001"], ["s002"], ["s003"]])
        self.assertEqual(parts[1]["text"], "b" * 1000)
        self.assertEqual(len(parts[1]["flags"]), 1)
        self.assertIn("dài hơn giới hạn Vbee", parts[1]["flags"][0])
        self.assertIn("cắt bằng tay", parts[1]["flags"][0])

    def test_prepare_writes_parts_and_inbox(self):
        with self.assertRaises(ValueError):
            self.v.prepare(self.pdir, "vi")  # no approved script
        self.approved(["Câu một.", "Câu hai."])
        out = self.v.prepare(self.pdir, "vi")
        self.assertEqual(len(out), 1)
        adir = os.path.join(self.pdir, "lang", "vi", "audio")
        parts = json.load(open(os.path.join(adir, "parts.json"), encoding="utf-8"))
        self.assertEqual(parts[0]["part"], "01")
        self.assertEqual(parts[0]["sentences"], ["s001", "s002"])
        self.assertTrue(os.path.isfile(os.path.join(adir, parts[0]["file"])) is False)
        self.assertEqual(open(os.path.join(adir, "parts", "01.txt"), encoding="utf-8").read(), "Câu một.\nCâu hai.")
        items = [i for i in self.inbox.open_items() if i["kind"] == "voice_needed"]
        self.assertEqual([i["text"] for i in items], ["Giọng VI: 1 phần chờ bạn tạo (Vbee)"])
        self.assertEqual(items[0]["screen"], "langs")
        self.assertEqual(items[0]["key"], "voice:001-a:vi")
        with self.assertRaises(ValueError):
            self.v.prepare(self.pdir, "en")  # en script not written/approved

    def test_drop_unknown_part_refused(self):
        self.approved(["Câu một.", "Câu hai."])
        self.v.prepare(self.pdir, "vi")
        for name in ("03.mp3", "01.wav", "../01.mp3", "1.mp3", "01.MP3x"):
            with self.assertRaises(ValueError):
                self.v.drop(self.pdir, "vi", name, MP3)
        with self.assertRaises(ValueError):
            self.v.drop(self.pdir, "en", "01.mp3", MP3)  # no parts prepared for en
        self.assertEqual(os.listdir(os.path.join(self.pdir, "lang", "vi", "audio", "parts")), ["01.txt"])

    def test_drop_non_mp3_refused(self):
        self.approved(["Câu một."])
        self.v.prepare(self.pdir, "vi")
        for data in (b"RIFF....WAVEfmt ", b"", b"<html>"):
            with self.assertRaises(ValueError):
                self.v.drop(self.pdir, "vi", "01.mp3", data)
        with mock.patch.object(self.v, "MAX_BYTES", 10):
            with self.assertRaises(ValueError):
                self.v.drop(self.pdir, "vi", "01.mp3", MP3)
        self.v.drop(self.pdir, "vi", "01.mp3", b"\xff\xfb\x90\x00" + b"\x00" * 32)  # MPEG frame sync

    def test_timing_waits_for_all_parts(self):
        self.approved(["a" * 500, "b" * 500, "c" * 500])  # 3 parts of 32 s
        parts = self.v.prepare(self.pdir, "vi")
        self.assertEqual(len(parts), 3)
        out = self.v.drop(self.pdir, "vi", "01.mp3", MP3)
        self.assertEqual(out["missing"], ["02", "03"])
        self.v.drop(self.pdir, "vi", "03.mp3", MP3)
        timing = lambda: [j for j in self.jobs.list_jobs() if j["kind"] == "timing_build"]
        self.assertEqual(timing(), [])
        self.assertTrue(any(i["key"] == "voice:001-a:vi" for i in self.inbox.open_items()))
        out = self.v.drop(self.pdir, "vi", "02.mp3", MP3)
        self.assertEqual(out["missing"], [])
        self.assertTrue(os.path.isfile(os.path.join(self.pdir, "lang", "vi", "audio", "parts", "02.mp3")))
        self.assertEqual([(j["params"], j["lane"]) for j in timing()], [({"project": "001-a", "lang": "vi"}, "cpu")])
        self.assertFalse(any(i["key"] == "voice:001-a:vi" for i in self.inbox.open_items()))
        st = self.v.status(self.pdir, "vi")
        self.assertEqual([p["present"] for p in st["parts"]], [True, True, True])
        self.assertEqual(st["parts"][0]["chars"], 500)

    def test_stale_after_edit(self):
        self.approved(["Câu một.", "Câu hai."])
        self.v.prepare(self.pdir, "vi")
        self.assertFalse(self.v.status(self.pdir, "vi")["stale"])
        self.v.drop(self.pdir, "vi", "01.mp3", MP3)
        d = doc(["Câu một.", "Câu hai.", "Câu ba."])
        self.script.save(self.pdir, d, "owner")
        self.script.approve(self.pdir, "owner")
        st = self.v.status(self.pdir, "vi")
        self.assertTrue(st["stale"])
        with self.assertRaises(ValueError):
            self.v.drop(self.pdir, "vi", "01.mp3", MP3)
        self.v.prepare(self.pdir, "vi")  # re-prepare clears it; the old mp3 is moved, never deleted
        st = self.v.status(self.pdir, "vi")
        self.assertFalse(st["stale"])
        self.assertEqual(st["missing"], ["01"])
        old = os.path.join(self.pdir, "lang", "vi", "audio", "parts", "old")
        moved = [f for _, _, files in os.walk(old) for f in files]
        self.assertIn("01.mp3", moved)

    def test_stale_after_text_edit_same_ids(self):
        """An edited sentence keeps its id: the part's text hash still tells that its mp3 is old."""
        self.approved(["Câu một.", "Câu hai."])
        rows = self.v.prepare(self.pdir, "vi")
        self.assertTrue(all(r.get("hash") for r in rows))
        self.v.drop(self.pdir, "vi", "01.mp3", MP3)
        self.approved(["Câu một đã sửa.", "Câu hai."])
        st = self.v.status(self.pdir, "vi")
        self.assertTrue(st["stale"])
        self.assertEqual(st["stale_parts"], ["01"])
        with self.assertRaises(ValueError):
            self.v.drop(self.pdir, "vi", "01.mp3", MP3)
        self.v.prepare(self.pdir, "vi")  # same ids, new text: the old mp3 is still moved away
        st = self.v.status(self.pdir, "vi")
        self.assertFalse(st["stale"])
        self.assertEqual(st["missing"], ["01"])
        with open(os.path.join(self.pdir, "lang", "vi", "audio", "parts", "01.txt"), encoding="utf-8") as f:
            self.assertIn("đã sửa", f.read())


if __name__ == "__main__":
    unittest.main()
