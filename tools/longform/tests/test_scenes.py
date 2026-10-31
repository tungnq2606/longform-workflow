import json
import os

from tools.longform.tests.scenefix import SceneBase, labels_doc, map_doc


class ScenesTest(SceneBase):
    def setUp(self):
        super().setUp()
        self.approve_script()

    def problems(self, data, labels=None):
        return self.scenes.validate(self.pdir, data, labels if labels is not None else labels_doc())

    def test_valid_doc_has_no_problems(self):
        self.assertEqual(self.problems(self.doc()), [])
        d = self.doc()
        d["beats"]["B01"]["map"] = map_doc()
        self.assertEqual(self.problems(d), [])

    def test_validator_unknown_refs(self):
        d = self.doc()
        b = d["beats"]["B01"]
        b["heroes"][0]["key"] = "hero-a/dance.happy"
        b["heroes"][0]["keys"][0]["key"] = "nobody/stand.calm"
        b["background"]["id"] = "library:castle-09"
        b["sfx"][0]["id"] = "laser-01"
        d["chapters"][0]["music"] = "pop-01"
        b["cards"][0]["sentence"] = "s777"
        b["cards"][0]["text_key"] = "nope"
        b["map"] = map_doc(fact="F999")
        text = "\n".join(self.problems(d))
        for needle in ("hero-a/dance.happy", "nobody/stand.calm", "castle-09", "laser-01", "pop-01", "s777", "nope", "F999"):
            self.assertIn(needle, text)
        self.assertIn("không có", text)

    def test_project_background_must_be_approved(self):
        d = self.doc()
        d["beats"]["B01"]["background"]["id"] = "project:BG01"
        d["beats"]["B01"]["crowds"] = []
        self.assertTrue(any("BG01" in p for p in self.problems(d)))
        self.approve_image()
        self.assertEqual(self.problems(d), [])

    def test_crowd_path_background_needs_library_geometry(self):
        self.approve_image()
        d = self.doc()
        d["beats"]["B01"]["background"]["id"] = "project:BG01"
        self.assertTrue(any("đường đi" in p for p in self.problems(d)))

    def test_validator_missing_beat(self):
        d = self.doc()
        d["beats"]["B09"] = d["beats"].pop("B01")
        text = "\n".join(self.problems(d))
        self.assertIn("B01", text)
        self.assertIn("B09", text)

    def test_border_needs_fact(self):
        d = self.doc()
        d["beats"]["B01"]["map"] = map_doc(fact=None, type="border")
        self.assertTrue(any("biên giới" in p for p in self.problems(d)))
        d["beats"]["B01"]["map"] = map_doc(fact=self.fact, type="border")
        self.assertEqual(self.problems(d), [])

    def test_labels_need_vi(self):
        labels = labels_doc()
        labels["date_1288"] = {"en": "1288"}
        self.assertTrue(any("date_1288" in p and "vi" in p for p in self.problems(self.doc(), labels)))

    def test_light_sound(self):
        d = self.doc()
        d["beats"]["B01"]["sfx"] = [{"sentence": "s001", "id": "oar-01", "offset": 0, "gain": 0.3}] * 4
        self.assertTrue(any("tối đa 3" in p for p in self.problems(d)))
        d["beats"]["B01"]["sfx"] = [{"sentence": "s001", "id": "oar-01", "offset": 0, "gain": 0.9}]
        self.assertTrue(any("gain" in p for p in self.problems(d)))

    def test_malformed_never_crashes(self):
        for bad in (None, [], {"beats": []}, {"chapters": [], "beats": {"B01": "x"}},
                    {"chapters": [], "beats": {"B01": {"heroes": "x", "background": 3}}}):
            self.assertTrue(self.problems(bad))

    def test_save_versions(self):
        v1 = self.scenes.save(self.pdir, self.doc(), "claude", labels=labels_doc())
        d = self.doc()
        d["beats"]["B01"]["crowds"][0]["count"] = 30
        v2 = self.scenes.save(self.pdir, d, "owner")
        self.assertEqual((v1, v2), (1, 2))
        cur = self.scenes.load(self.pdir)
        self.assertEqual((cur["version"], cur["updated_by"]), (2, "owner"))
        self.assertEqual(cur["beats"]["B01"]["crowds"][0]["count"], 30)
        with open(os.path.join(self.pdir, "scenes", "versions", "v001.json")) as f:
            self.assertEqual(json.load(f)["beats"]["B01"]["crowds"][0]["count"], 20)
        self.assertEqual(self.scenes.labels(self.pdir)["date_1288"]["vi"], "Năm 1288")
        self.assertEqual(self.scenes.labels(self.pdir)["modern_map"]["ja"], "現代の地図")  # built in
        with self.assertRaisesRegex(ValueError, "đã đổi"):
            self.scenes.save(self.pdir, d, "owner", base=1)

    def test_claude_scenes_requires_approved_script(self):
        self.approve_script(approved=False)
        with self.assertRaisesRegex(ValueError, "chốt"):
            self.jobs.enqueue("claude_scenes", {"project": "001-a"}, "001-a", "c")
        self.approve_script()
        with self.assertRaisesRegex(ValueError, "ảnh"):
            self.jobs.enqueue("claude_scenes", {"project": "001-a"}, "001-a", "c")
        self.approve_image()
        j = self.jobs.enqueue("claude_scenes", {"project": "001-a"}, "001-a", "c")
        self.assertEqual(j["lane"], "claude")
        self.assertEqual(os.path.basename(j["argv"][0]), "fake_claude.py")
        self.assertNotIn("--add-dir", j["argv"])
        self.assertFalse(any("skip-permissions" in a for a in j["argv"]))
        run = j["params"]["run"]
        for name in ("SCENES.md", "script.json", "images.json", "kits.json", "library.json", "audio.json", "facts.json"):
            self.assertTrue(os.path.isfile(os.path.join(run, name)), name)
        with open(os.path.join(run, "images.json")) as f:
            imgs = json.load(f)
        self.assertEqual([i["id"] for i in imgs], ["BG01"])
        self.assertTrue(os.path.isfile(os.path.join(run, imgs[0]["thumb"])))
        with open(os.path.join(run, "kits.json")) as f:
            self.assertEqual(json.load(f)[0]["poses"], ["point.angry", "stand.calm"])
        with open(os.path.join(run, "SCENES.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("result.json", text)
        self.assertNotIn("$", text.replace("$$", ""))  # every template value was filled

    def test_claude_scenes_on_end_validates(self):
        self.approve_image()
        bad = self.doc()
        bad["beats"]["B01"]["heroes"][0]["key"] = "hero-a/fly.happy"
        self.fixture({"result.json": {"scenes": bad, "labels": labels_doc()}})
        j = self.jobs.enqueue("claude_scenes", {"project": "001-a"}, "001-a", "c")
        self.assertEqual(self.run_job(j), "done")
        self.assertIsNone(self.scenes.load(self.pdir))
        self.assertTrue(any("fly.happy" in i["text"] for i in self.inbox.open_items()))

        self.fixture({"result.json": {"scenes": self.doc(), "labels": labels_doc()}})
        j = self.jobs.enqueue("claude_scenes", {"project": "001-a"}, "001-a", "c")
        self.assertEqual(self.run_job(j), "done")
        self.assertEqual(self.scenes.load(self.pdir)["version"], 1)
        self.assertEqual(self.scenes.labels(self.pdir)["date_1288"]["en"], "1288")
        self.assertTrue(any(i["kind"] == "scenes_ready" for i in self.inbox.open_items()))
        from tools.longform import progress
        self.assertEqual({s["id"]: s["state"] for s in progress.get(self.pdir)["steps"]}["scenes"], "wait")

    def test_empty_audio_library_warns_on_scene_writing(self):
        self.approve_image()
        with open(os.path.join(self.root, "library", "audio", "index.json"), "w") as f:
            json.dump({"music": [], "sfx": []}, f)
        self.jobs.enqueue("claude_scenes", {"project": "001-a"}, "001-a", "c")
        self.assertTrue(any(i["kind"] == "audio_missing" for i in self.inbox.open_items()))
