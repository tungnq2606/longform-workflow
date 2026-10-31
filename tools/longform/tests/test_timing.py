import json
import math
import os
import shutil
import struct
import tempfile
import unittest
import wave
from unittest import mock

WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SR = 16000


def write_wav(path, pattern):
    """pattern: [("tone"|"gap", seconds), ...] -> a 16 kHz mono 16-bit WAV."""
    frames = []
    for kind, sec in pattern:
        n = int(sec * SR)
        if kind == "tone":
            frames += [int(8000 * math.sin(2 * math.pi * 220 * i / SR)) for i in range(n)]
        else:
            frames += [0] * n
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(struct.pack("<%dh" % len(frames), *frames))


def script_doc(beats):
    """beats: {"B01": [("s001", "text"), ...]} in order, all in chapter C01."""
    return {"lang": "vi", "version": 1, "approved": True, "chapters": [{"id": "C01", "title": "Mở đầu", "beats": [
        {"id": b, "goal": "", "sentences": [{"id": i, "text": t, "facts": []} for i, t in ss]} for b, ss in beats.items()]}]}


class TimingTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "config"))
        shutil.copy(os.path.join(WS, "config", "languages.json"), os.path.join(self.root, "config"))
        os.environ["LONGFORM_ROOT"] = self.root
        from tools.longform import progress, project, timing
        self.t, self.progress = timing, progress
        self.pdir = project.create_project(1, "a", "A", ["en"])
        self.p = mock.patch.object(timing, "decode", lambda mp3, wav: shutil.copyfile(mp3, wav))
        self.p.start()

    def tearDown(self):
        self.p.stop()
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def wav(self, pattern, name="x.wav"):
        p = os.path.join(self.root, name)
        write_wav(p, pattern)
        return p

    def test_pauses_found(self):
        p = self.wav([("tone", 1.0), ("gap", 0.5), ("tone", 1.0), ("gap", 0.3), ("tone", 0.5)])
        ps, dur = self.t.pauses(p)
        self.assertAlmostEqual(dur, 3.3, places=2)
        self.assertEqual(len(ps), 2)
        self.assertAlmostEqual(ps[0][0], 1.0, delta=0.03)
        self.assertAlmostEqual(ps[0][1], 1.5, delta=0.03)
        self.assertAlmostEqual(ps[1][0], 2.5, delta=0.03)

    def test_split_by_longest_pauses(self):
        # three sentences, four pauses: the two longest (0.8 s, 0.6 s) are the boundaries, kept in time order
        ps = [(0.0, 0.2), (1.0, 1.15), (2.0, 2.8), (3.5, 3.65), (4.5, 5.1), (6.0, 6.3)]
        rows = self.t.split_part(ps, 6.3, [("s1", "aaaa"), ("s2", "bbbb"), ("s3", "cccc")])
        self.assertEqual([r["id"] for r in rows], ["s1", "s2", "s3"])
        self.assertEqual([(r["start"], r["end"]) for r in rows], [(0.2, 2.0), (2.8, 4.5), (5.1, 6.0)])
        self.assertFalse(any(r["approx"] for r in rows))

    def test_too_few_pauses_falls_back(self):
        # a fast speaker: three sentences but only one inner pause -> split by character count, marked approx
        ps = [(2.0, 2.2)]
        rows = self.t.split_part(ps, 6.0, [("s1", "a" * 10), ("s2", "b" * 20), ("s3", "c" * 30)])
        self.assertEqual([r["id"] for r in rows], ["s1", "s2", "s3"])
        self.assertTrue(all(r["approx"] for r in rows))
        self.assertAlmostEqual(rows[0]["start"], 0.0)
        self.assertAlmostEqual(rows[0]["end"], 1.0)
        self.assertAlmostEqual(rows[1]["end"], 3.0)
        self.assertAlmostEqual(rows[2]["end"], 6.0)
        for a, b in zip(rows, rows[1:]):
            self.assertLessEqual(a["end"], b["start"])

    def test_one_sentence_part(self):
        rows = self.t.split_part([(0.0, 0.3), (2.0, 2.4)], 2.4, [("s1", "x")])
        self.assertEqual(rows, [{"id": "s1", "start": 0.3, "end": 2.0, "approx": False}])

    def write_parts(self, lang, parts):
        d = os.path.join(self.pdir, "lang", lang, "audio")
        rows = []
        for name, sentences, pattern in parts:
            if pattern is not None:
                write_wav(os.path.join(d, name + ".mp3"), pattern)
            rows.append({"part": name, "file": name + ".mp3", "sentences": sentences})
        with open(os.path.join(d, "parts.json"), "w") as f:
            json.dump(rows, f)

    def test_build_beats_and_gap(self):
        from tools.longform import script
        script.save(self.pdir, script_doc({"B01": [("s001", "Một hai."), ("s002", "Ba bốn.")], "B02": [("s003", "Năm.")]}), "t")
        self.write_parts("vi", [("01", ["s001", "s002"], [("tone", 1.0), ("gap", 0.5), ("tone", 1.0)]),
                                ("02", ["s003"], [("tone", 1.0)])])
        out = self.t.build(self.pdir, "vi")
        with open(os.path.join(self.pdir, "lang", "vi", "timing.json")) as f:
            self.assertEqual(json.load(f), out)
        self.assertEqual(out["lang"], "vi")
        self.assertEqual([p["part"] for p in out["parts"]], ["01", "02"])
        self.assertAlmostEqual(out["parts"][1]["start"], 2.5 + self.t.GAP, places=2)
        self.assertAlmostEqual(out["duration"], 2.5 + self.t.GAP + 1.0, places=2)
        self.assertEqual([b["id"] for b in out["beats"]], ["B01", "B02"])
        b1, b2 = out["beats"]
        self.assertEqual([s["id"] for s in b1["sentences"]], ["s001", "s002"])
        self.assertAlmostEqual(b1["sentences"][1]["start"], 1.5, delta=0.03)
        self.assertAlmostEqual(b2["start"], 2.9, delta=0.03)
        self.assertAlmostEqual(b2["sentences"][0]["start"], 2.9, delta=0.03)
        langs = {l["code"]: l["parts"] for l in self.progress.get(self.pdir)["langs"]}
        self.assertEqual(langs["vi"]["voice"], "done")

    def test_build_uses_language_script(self):
        from tools.longform import script
        script.save(self.pdir, script_doc({"B01": [("s001", "Một.")]}), "t")
        en = script_doc({"B01": [("s001", "One."), ("s002", "Two.")]})
        en["lang"] = "en"
        os.makedirs(os.path.join(self.pdir, "lang", "en", "script"), exist_ok=True)
        with open(os.path.join(self.pdir, "lang", "en", "script", "script.json"), "w") as f:
            json.dump(en, f)
        self.write_parts("en", [("01", ["s001", "s002"], [("tone", 1.0), ("gap", 0.5), ("tone", 1.0)])])
        out = self.t.build(self.pdir, "en")
        self.assertEqual([s["id"] for s in out["beats"][0]["sentences"]], ["s001", "s002"])

    def test_build_refuses_unknown_sentence(self):
        from tools.longform import script
        script.save(self.pdir, script_doc({"B01": [("s001", "Một.")]}), "t")
        self.write_parts("vi", [("01", ["s001", "s009"], [("tone", 1.0)])])
        with self.assertRaisesRegex(ValueError, "s009"):
            self.t.build(self.pdir, "vi")

    def test_missing_parts(self):
        self.assertEqual(self.t.missing_parts(self.pdir, "vi"), [])  # nothing prepared yet: nothing listed as missing
        self.write_parts("vi", [("01", ["s001"], [("tone", 1.0)]), ("02", ["s002"], None), ("03", ["s003"], None)])
        self.assertEqual(self.t.missing_parts(self.pdir, "vi"), ["02", "03"])
        with self.assertRaisesRegex(ValueError, "thiếu giọng phần 02"):
            self.t.build(self.pdir, "vi")

    def test_cli_job_kind(self):
        from tools.longform import jobs
        j = jobs.enqueue("timing_build", {"project": "001-a", "lang": "en"}, "001-a", "dò thời điểm")
        self.assertEqual(j["lane"], "cpu")
        self.assertEqual(j["argv"][1:], ["-m", "tools.longform.timing", "001-a", "en"])
        with self.assertRaises(ValueError):
            jobs.enqueue("timing_build", {"project": "001-a", "lang": "xx"}, "001-a", "x")


if __name__ == "__main__":
    unittest.main()
