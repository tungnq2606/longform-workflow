"""Plan 5 render per language: checks, assets, props, subtitles, chapters, previews. Remotion is never run."""
import json
import os
import subprocess
from unittest import mock

from tools.longform.tests.scenefix import SceneBase, labels_doc, map_doc

TIMING = {"lang": "vi", "duration": 8.0, "beats": [
    {"id": "B01", "start": 0.2, "end": 8.0, "sentences": [{"id": "s001", "start": 0.2, "end": 3.0}, {"id": "s002", "start": 3.4, "end": 8.0}]}],
    "parts": [{"part": "01", "start": 0.0, "duration": 4.0, "approx": False}, {"part": "02", "start": 4.4, "duration": 3.6, "approx": False}]}


class RenderLangTest(SceneBase):
    def setUp(self):
        super().setUp()
        from tools.longform import render
        self.r = render
        self.approve_script()
        self.approve_image()
        self.scenes.save(self.pdir, self.doc(), "claude", labels=labels_doc())
        self.calls = []
        self.p_run = mock.patch.object(render.subprocess, "run", self.fake_run)
        self.p_run.start()
        fonts = os.path.join(self.root, "tools", "kit", "fonts")
        os.makedirs(fonts)
        open(os.path.join(fonts, "BeVietnamPro-ExtraBold.ttf"), "wb").close()

    def tearDown(self):
        self.p_run.stop()
        super().tearDown()

    def fake_run(self, cmd, cwd=None, **kw):
        self.calls.append(cmd)
        if "remotion" in cmd:
            out = cmd[5]
            os.makedirs(os.path.dirname(out), exist_ok=True)
            open(out, "wb").close()
        return subprocess.CompletedProcess(cmd, 0)

    def voice(self, parts=("01", "02"), present=("01", "02"), timing=True):
        d = os.path.join(self.pdir, "lang", "vi", "audio")
        with open(os.path.join(d, "parts.json"), "w") as f:
            json.dump([{"part": p, "file": p + ".mp3", "sentences": ["s00%d" % (i + 1)]} for i, p in enumerate(parts)], f)
        for p in present:
            open(os.path.join(d, p + ".mp3"), "wb").close()
        if timing:
            with open(os.path.join(self.pdir, "lang", "vi", "timing.json"), "w") as f:
                json.dump(TIMING, f)

    def test_render_refuses_missing_voice(self):
        self.voice(present=("01",))
        with self.assertRaisesRegex(ValueError, "thiếu giọng phần 02"):
            self.r.render_lang(self.pdir, "vi")
        self.assertFalse(any("remotion" in c for c in self.calls))  # never a silent video

    def test_render_refuses_missing_timing_and_bad_scenes(self):
        self.voice(timing=False)
        with self.assertRaisesRegex(ValueError, "thời điểm"):
            self.r.render_lang(self.pdir, "vi")
        self.voice()
        d = self.doc()
        d["beats"]["B01"]["heroes"][0]["key"] = "hero-a/gone.sad"
        with open(os.path.join(self.pdir, "scenes", "scenes.json"), "w") as f:
            json.dump(d, f)
        with self.assertRaisesRegex(ValueError, "gone.sad"):
            self.r.render_lang(self.pdir, "vi")

    def test_render_refuses_untranslated_labels(self):
        from tools.longform import project
        meta = project.load_project(self.pdir)
        meta["languages"].append("de")
        with open(os.path.join(self.pdir, "project.json"), "w") as f:
            json.dump(meta, f)
        self.assertTrue(any("date_1288" in p and "de" in p for p in self.r.check(self.pdir, "de")))

    def test_render_writes_video_srt_chapters(self):
        self.voice()
        out = self.r.render_lang(self.pdir, "vi")
        self.assertEqual(out, os.path.join(self.pdir, "lang", "vi", "render", "001-a_vi_1440p.mp4"))
        remotion = [c for c in self.calls if "remotion" in c]
        self.assertEqual(remotion[0][:5], ["npx", "remotion", "render", "src/index.ts", "Longform"])
        props_arg = [a for a in remotion[0] if a.startswith("--props=")][0][len("--props="):]
        self.assertTrue(os.path.isfile(props_arg))  # a file: props are too big for one argv
        self.assertTrue(self.calls.index([c for c in self.calls if "tsc" in c][0]) < self.calls.index(remotion[0]))
        rdir = os.path.join(self.pdir, "lang", "vi", "render")
        self.assertTrue(os.path.isfile(os.path.join(rdir, "001-a_vi.srt")))
        self.assertTrue(os.path.isfile(os.path.join(rdir, "chapters.txt")))
        langs = {l["code"]: l["parts"] for l in __import__("tools.longform.progress", fromlist=["x"]).get(self.pdir)["langs"]}
        self.assertEqual(langs["vi"]["render"], "done")

    def test_srt_from_timing(self):
        self.voice()
        srt = self.r.srt(self.pdir, "vi")
        self.assertEqual(srt, "1\n00:00:00,200 --> 00:00:03,000\nBạn có biết không?\n\n"
                              "2\n00:00:03,400 --> 00:00:08,000\nRồi quân Nguyên đến sông Bạch Đằng.\n")

    def test_chapters_start_at_zero(self):
        self.voice()
        self.assertEqual(self.r.chapters_txt(self.pdir, "vi"), "0:00 Mở đầu\n")
        doc = json.load(open(os.path.join(self.pdir, "script", "script.json")))
        doc["chapters"].append({"id": "C02", "title": "Trận đánh", "beats": [{"id": "B02", "goal": "", "sentences": [
            {"id": "s003", "text": "Thuyền giặc mắc cọc.", "facts": []}]}]})
        with open(os.path.join(self.pdir, "script", "script.json"), "w") as f:
            json.dump(doc, f)
        t = dict(TIMING, duration=80.0)
        t["beats"] = TIMING["beats"] + [{"id": "B02", "start": 75.5, "end": 80, "sentences": [{"id": "s003", "start": 75.5, "end": 80}]}]
        with open(os.path.join(self.pdir, "lang", "vi", "timing.json"), "w") as f:
            json.dump(t, f)
        self.assertEqual(self.r.chapters_txt(self.pdir, "vi"), "0:00 Mở đầu\n1:15 Trận đánh\n")

    def test_assets_only_used_files(self):
        self.voice()
        lib = os.path.join(self.root, "library")
        os.makedirs(os.path.join(lib, "characters", "hero-b"))
        open(os.path.join(lib, "backgrounds", "other-01.png"), "wb").close()
        open(os.path.join(lib, "audio", "sfx", "unused-01.mp3"), "wb").close()
        a = self.r.assets(self.pdir, "vi")
        self.assertIn("library/backgrounds/river-01.png", a)
        self.assertIn("library/characters/hero-a", a)
        self.assertIn("library/audio/music/open-01.mp3", a)
        self.assertIn("library/audio/sfx/oar-01.mp3", a)
        self.assertIn("projects/001-a/lang/vi/audio/01.mp3", a)
        self.assertIn("tools/kit/fonts/BeVietnamPro-ExtraBold.ttf", a)
        for unused in ("library/backgrounds/other-01.png", "library/characters/hero-b", "library/audio/sfx/unused-01.mp3",
                       "library/maps/vn_region.json"):
            self.assertNotIn(unused, a)
        d = self.doc()
        d["beats"]["B01"]["map"] = map_doc()
        self.scenes.save(self.pdir, d, "t")
        self.assertIn("library/maps/vn_region.json", self.r.assets(self.pdir, "vi"))

    def test_props_paths_relative(self):
        self.voice()
        p = self.r.props(self.pdir, "vi")
        self.assertEqual(p["lang"], "vi")
        self.assertEqual(p["audio"]["voice"], [{"file": "projects/001-a/lang/vi/audio/01.mp3", "start": 0.0},
                                               {"file": "projects/001-a/lang/vi/audio/02.mp3", "start": 4.4}])
        self.assertEqual(p["audio"]["music"], {"C01": "library/audio/music/open-01.mp3"})
        self.assertEqual(p["audio"]["sfx"], [{"id": "oar-01", "file": "library/audio/sfx/oar-01.mp3"}])
        self.assertEqual(p["backgrounds"]["library:river-01"]["image"], "library/backgrounds/river-01.png")
        self.assertEqual(p["backgrounds"]["library:river-01"]["path"], [[2600, 1100], [800, 700]])
        self.assertEqual(p["chapters"], [{"id": "C01", "title": "Mở đầu", "beats": ["B01"], "titleCard": True}])
        self.assertEqual(p["anchors"]["s002"], {"beat": "B01", "index": 1, "count": 2})
        self.assertEqual(p["font"], {"family": "BeVietnamPro", "file": "tools/kit/fonts/BeVietnamPro-ExtraBold.ttf"})
        assets = set(self.r.assets(self.pdir, "vi"))
        files = [v["file"] for v in p["audio"]["voice"]] + list(p["audio"]["music"].values()) + \
                [s["file"] for s in p["audio"]["sfx"]] + [b["image"] for b in p["backgrounds"].values()] + [p["font"]["file"]]
        for f in files:
            self.assertFalse(os.path.isabs(f))
            self.assertIn(f, assets)

    def test_missing_audio_file_is_a_warning_not_a_block(self):
        self.voice()
        os.remove(os.path.join(self.root, "library", "audio", "music", "open-01.mp3"))
        self.assertEqual(self.r.check(self.pdir, "vi"), [])
        self.assertEqual(self.r.props(self.pdir, "vi")["audio"]["music"], {})
        self.assertTrue(any("open-01" in w for w in self.r.warnings(self.pdir)))

    def test_still_beat_middle_frame(self):
        out = self.r.still_beat(self.pdir, "B01")  # no voice yet: estimated timing
        self.assertEqual(out, os.path.join(self.pdir, "images", "previews", "B01.png"))
        still = [c for c in self.calls if "still" in c][0]
        frame = int([a for a in still if a.startswith("--frame=")][0].split("=")[1])
        self.assertGreater(frame, 0)
        self.voice()
        self.calls.clear()
        self.r.still_beat(self.pdir, "B01")
        still = [c for c in self.calls if "still" in c][0]
        self.assertIn("--frame=%d" % round((0 + 8.0) / 2 * 30), still)  # middle of B01 (beat runs from frame 0)
        with self.assertRaises(KeyError):
            self.r.still_beat(self.pdir, "B77")

    def test_job_kinds(self):
        j = self.jobs.enqueue("render_lang", {"project": "001-a", "lang": "vi"}, "001-a", "render vi")
        self.assertEqual(j["lane"], "render")
        self.assertEqual(j["argv"][1:], ["-m", "tools.longform.render", "lang", "001-a", "vi"])
        s = self.jobs.enqueue("render_still", {"project": "001-a", "beat": "B01"}, "001-a", "still")
        self.assertEqual(s["argv"][1:], ["-m", "tools.longform.render", "still", "001-a", "B01"])
        with self.assertRaises(ValueError):
            self.jobs.enqueue("render_still", {"project": "001-a", "beat": "../x"}, "001-a", "x")
        with self.assertRaises(ValueError):
            self.jobs.enqueue("render_lang", {"project": "001-a", "lang": "xx"}, "001-a", "x")

    def test_render_done_inbox(self):
        job = {"id": "a" * 32, "kind": "render_lang", "status": "done", "project": "001-a", "params": {"project": "001-a", "lang": "vi"}, "label": "x"}
        self.r.render_end(job)
        self.r.render_end(job)
        items = [i for i in self.inbox.open_items() if i["kind"] == "render_done"]
        self.assertEqual(len(items), 1)
        self.assertIn("Đã render VI", items[0]["text"])
        self.assertIn("001-a_vi_1440p.mp4", items[0]["text"])
