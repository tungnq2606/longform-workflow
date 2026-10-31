import json
import os
import threading
import unittest

from tools.longform.tests.imgfix import ImgBase, bg_spec, pose_spec, prop_spec


class ImagesTest(ImgBase):
    def test_add_ids_per_type(self):
        a = self.images.add(self.pdir, "bg", bg_spec(), beat="B01")
        b = self.images.add(self.pdir, "bg", bg_spec(), beat="B02")
        p = self.images.add(self.pdir, "prop", prop_spec(), beat="B02")
        h = self.images.add(self.pdir, "pose", pose_spec(), kit="hero-a", pose_key="point.determined")
        self.assertEqual([a["id"], b["id"], p["id"], h["id"]], ["BG01", "BG02", "P01", "H01"])
        self.assertEqual(a["state"], "queued")
        self.assertEqual(a["attempts"], 0)
        self.assertEqual(a["beat"], "B01")
        self.assertIn("Shot: wide establishing shot", a["prompt"])
        self.assertIn("Exactly one figure", h["prompt"])
        self.assertEqual(h["refs"], ["library/characters/hero-a/model_sheet.png", "library/characters/hero-a/stand_calm.png"])
        self.assertEqual([i["id"] for i in self.images.load(self.pdir)], ["BG01", "BG02", "P01", "H01"])
        self.assertEqual(self.images.counts(self.pdir), {"queued": 4})

    def test_bg_must_not_always_has_people_and_text(self):
        line = "people, human figures, animals, text, letters"
        spec = bg_spec()
        a = self.images.add(self.pdir, "bg", spec)
        self.assertEqual(a["spec"]["must_not"], ["boats with sails", line])
        self.assertIn("- " + line, a["prompt"])
        self.assertEqual(spec["must_not"], ["boats with sails"])  # the caller's spec is not changed
        b = self.images.add(self.pdir, "bg", bg_spec(must_not=[line]))
        self.assertEqual(b["spec"]["must_not"], [line])  # never twice
        p = self.images.add(self.pdir, "prop", prop_spec())
        self.assertNotIn(line, p["spec"]["must_not"])

    def test_add_validates_spec(self):
        with self.assertRaises(ValueError) as cm:
            self.images.add(self.pdir, "bg", bg_spec(people="two soldiers"))
        self.assertIn("people", str(cm.exception))
        with self.assertRaises(ValueError):
            self.images.add(self.pdir, "scene", bg_spec())
        with self.assertRaises(ValueError):  # a pose needs an existing kit and a pose key
            self.images.add(self.pdir, "pose", pose_spec(), kit="nobody", pose_key="stand.calm")
        with self.assertRaises(ValueError):
            self.images.add(self.pdir, "pose", pose_spec(), kit="hero-a", pose_key="Stand Calm")
        self.assertEqual(self.images.load(self.pdir), [])

    def test_update_history(self):
        self.images.add(self.pdir, "bg", bg_spec())
        it = self.images.update(self.pdir, "BG01", state="generating")
        it = self.images.update(self.pdir, "BG01", score=4, state="pass", note="đẹp")
        self.assertEqual([h["event"] for h in it["history"]], ["queued", "generating", "pass"])
        self.assertEqual(it["history"][-1]["score"], 4)
        self.assertEqual(it["history"][-1]["note"], "đẹp")
        self.assertNotIn("note", it)
        n = len(it["history"])
        it = self.images.update(self.pdir, "BG01", problems=["x"])  # no state change: no event
        self.assertEqual(len(it["history"]), n)
        with self.assertRaises(KeyError):
            self.images.update(self.pdir, "BG99", state="pass")
        with self.assertRaises(ValueError):
            self.images.update(self.pdir, "BG01", state="lost")

    def test_concurrent_item_updates(self):
        for _ in range(8):
            self.images.add(self.pdir, "bg", bg_spec())
        ids = [i["id"] for i in self.images.load(self.pdir)]
        errors = []

        def work(i):
            try:
                self.images.update(self.pdir, i, state="reviewing", score=None)
                self.images.update(self.pdir, i, state="pass", score=5)
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        ts = [threading.Thread(target=work, args=(i,)) for i in ids]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(self.images.counts(self.pdir), {"pass": 8})
        with open(os.path.join(self.pdir, "images", "items.json")) as f:
            self.assertEqual(len(json.load(f)), 8)

    def test_step_follows_states(self):
        self.images.add(self.pdir, "bg", bg_spec())
        self.images.add(self.pdir, "bg", bg_spec())
        self.assertEqual(self.step(), "doing")
        self.images.update(self.pdir, "BG01", state="wait")
        self.assertEqual(self.step(), "doing")  # BG02 still queued
        self.images.update(self.pdir, "BG02", state="pass")
        self.assertEqual(self.step(), "wait")
        self.images.update(self.pdir, "BG01", state="approved")
        self.images.update(self.pdir, "BG02", state="rejected")
        self.assertEqual(self.step(), "done")

    def test_reuse_library_background_approved(self):
        it = self.images.add(self.pdir, "bg", {"setting": "river"}, beat="B03", reuse="river-01")
        self.assertEqual(it["state"], "approved")
        self.assertEqual(it["files"]["final"], "library/backgrounds/river-01.png")
        self.assertEqual(self.step(), "done")
        with self.assertRaises(ValueError):
            self.images.add(self.pdir, "bg", bg_spec(), reuse="no-such-bg")
        with self.assertRaises(ValueError):
            self.images.add(self.pdir, "pose", pose_spec(), kit="hero-a", pose_key="a.b", reuse="river-01")


if __name__ == "__main__":
    unittest.main()
