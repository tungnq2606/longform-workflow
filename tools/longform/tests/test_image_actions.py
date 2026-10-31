import json
import os
import shutil
import unittest
from unittest import mock

from PIL import Image

from tools.longform.tests.imgfix import ImgBase, bg_spec, pose_spec
from tools.longform.tests.imgs import figure


class ImageActionsTest(ImgBase):
    def setUp(self):
        super().setUp()
        from tools.longform import castsheet, cutout, imagegen, kit, workers  # noqa: F401  workers registers job kinds
        self.kit, self.cutout, self.castsheet = kit, cutout, castsheet
        self.ts = os.path.join(self.root, "kits.generated.ts")
        self.patches += [mock.patch.object(kit, "TS_OUT", self.ts),
                         mock.patch.object(imagegen, "generate", mock.Mock(side_effect=AssertionError("no AI here")))]
        for p in self.patches[-2:]:
            p.start()

    def queued(self, kind):
        return [j for j in self.jobs.list_jobs() if j["kind"] == kind and j["status"] == "queued"]

    def bg_done(self, state="pass"):
        self.images.add(self.pdir, "bg", bg_spec())
        final = os.path.join(self.pdir, "images", "final", "BG01.png")
        os.makedirs(os.path.dirname(final), exist_ok=True)
        Image.new("RGB", (2816, 1584), (100, 120, 90)).save(final)
        return self.images.update(self.pdir, "BG01", state=state, score=4,
                                  files={"raw": None, "final": self.images.rel(final), "cutout": None})

    def pose_done(self, through_bottom=False):
        self.images.add(self.pdir, "pose", pose_spec(), kit="hero-a", pose_key="point.determined")
        final = figure(os.path.join(self.pdir, "images", "H01_green.png"), size=(640, 1100), cx=320, bottom=1000,
                       through_bottom=through_bottom)
        cut = os.path.join(self.pdir, "images", "H01_cut.png")
        self.cutout.cut(final, cut)
        self.inbox.add(self.pid, "image_review", "H01 được 3/5", screen="images", key="img:001-a:H01")
        return self.images.update(self.pdir, "H01", state="wait", score=3,
                                  files={"raw": None, "final": self.images.rel(final), "cutout": self.images.rel(cut)})

    def test_approve_bg(self):
        self.bg_done()
        self.inbox.add(self.pid, "image_review", "BG01 được 3/5", screen="images", key="img:001-a:BG01")
        it = self.images.approve(self.pdir, "BG01")
        self.assertEqual(it["state"], "approved")
        self.assertEqual(self.inbox.open_items(), [])
        self.assertEqual(self.step(), "done")
        self.images.add(self.pdir, "bg", bg_spec())
        with self.assertRaises(ValueError):  # nothing drawn yet
            self.images.approve(self.pdir, "BG02")

    def test_approve_pose_runs_cutout_check(self):
        self.pose_done(through_bottom=True)  # feet cut off by the frame
        with self.assertRaises(ValueError) as cm:
            self.images.approve(self.pdir, "H01")
        self.assertIn("chạm mép", str(cm.exception))
        self.assertEqual(self.images.get(self.pdir, "H01")["state"], "wait")
        self.assertNotIn("point.determined", self.kit.load_kit("hero-a")["images"])
        self.assertFalse(os.path.exists(self.ts))

    def test_approve_pose_adds_to_kit(self):
        self.pose_done()
        it = self.images.approve(self.pdir, "H01")
        self.assertEqual(it["state"], "approved")
        k = self.kit.load_kit("hero-a")
        self.assertIn("point.determined", k["images"])
        self.assertTrue(os.path.isfile(os.path.join(self.kit.kit_dir("hero-a"), "point_determined.png")))
        self.assertIn("'hero-a/point.determined'", open(self.ts).read())
        self.assertEqual(self.inbox.open_items(), [])

    def test_redo_requeues_with_note(self):
        it = self.bg_done(state="wait")
        self.images.update(self.pdir, "BG01", attempts=2)
        self.inbox.add(self.pid, "image_review", "BG01 được 3/5", screen="images", key="img:001-a:BG01")
        it = self.images.redo(self.pdir, "BG01", "Bỏ ngôi chùa bên trái")
        self.assertEqual((it["state"], it["fix"], it["attempts"]), ("queued", "Bỏ ngôi chùa bên trái", 2))
        self.assertEqual([j["params"]["item"] for j in self.queued("agy_image")], ["BG01"])
        self.assertEqual(self.inbox.open_items(), [])
        with self.assertRaises(ValueError):  # already queued
            self.images.redo(self.pdir, "BG01", "x")

    def test_redo_reject_running_state_without_live_job(self):
        """A worker that died left the item generating/reviewing with no job: the owner can still redo or reject it."""
        self.bg_done(state="generating")
        it = self.images.redo(self.pdir, "BG01", "vẽ lại")
        self.assertEqual(it["state"], "queued")
        self.images.update(self.pdir, "BG01", state="generating")
        with self.assertRaises(ValueError):  # now a live agy_image job holds it
            self.images.reject(self.pdir, "BG01")
        with self.assertRaises(ValueError):
            self.images.redo(self.pdir, "BG01", "x")
        self.jobs.stop(self.queued("agy_image")[0]["id"])
        self.assertEqual(self.images.get(self.pdir, "BG01")["state"], "failed")  # on_end of the stopped job
        self.images.update(self.pdir, "BG01", state="reviewing")
        self.assertEqual(self.images.reject(self.pdir, "BG01")["state"], "rejected")

    def test_recover_marks_image_failed(self):
        self.bg_done(state="generating")
        j = self.jobs.enqueue("agy_image", {"project": self.pid, "item": "BG01"}, self.pid, "agy vẽ BG01")
        self.jobs._write(dict(self.jobs.get(j["id"]), status="running", pid=999999))
        self.jobs.recover()
        self.assertEqual(self.images.get(self.pdir, "BG01")["state"], "failed")
        self.assertEqual(self.images.approve(self.pdir, "BG01")["state"], "approved")

    def test_reject_and_approve_many(self):
        self.bg_done()
        self.images.add(self.pdir, "bg", bg_spec())  # BG02 still queued: cannot be approved
        out = self.images.approve_many(self.pdir, ["BG01", "BG02", "BG09"])
        self.assertEqual(out["approved"], ["BG01"])
        self.assertEqual(sorted(out["errors"]), ["BG02", "BG09"])
        self.assertEqual(self.images.reject(self.pdir, "BG02")["state"], "rejected")
        self.assertIn("đã duyệt rồi", self.images.approve_many(self.pdir, ["BG01"])["errors"]["BG01"])

    def test_save_background(self):
        self.bg_done(state="approved")
        slug = self.images.save_background(self.pdir, "BG01", "Sông Bạch Đằng lúc triều xuống")
        self.assertEqual(slug, "song-bach-dang-luc-trieu-xuong")
        lib = os.path.join(self.root, "library", "backgrounds")
        self.assertTrue(os.path.isfile(os.path.join(lib, slug + ".png")))
        self.assertEqual(json.load(open(os.path.join(lib, slug + ".json"))), {"horizonY": None, "groundY": None, "path": []})
        with self.assertRaises(ValueError):  # same name twice
            self.images.save_background(self.pdir, "BG01", "Sông Bạch Đằng lúc triều xuống")

    def test_cast_sheet_composed_locally(self):
        self.pose_done()
        self.images.approve(self.pdir, "H01")
        path = self.castsheet.build(self.pdir)
        self.assertEqual(path, os.path.join(self.pdir, "images", "cast_sheet.png"))
        im = Image.open(path).convert("RGB")
        self.assertEqual(im.getpixel((2, 2)), (255, 255, 255))
        px = im.load()
        cols = [any(px[x, y] != (255, 255, 255) for y in range(40, 40 + 480, 4)) for x in range(im.size[0])]
        runs, gap = 0, 99
        for c in cols:  # a cell starts after a white gutter of at least 20 px
            if c and gap >= 20:
                runs += 1
            gap = 0 if c else gap + 1
        self.assertEqual(runs, 2)  # stand.calm and point.determined side by side


if __name__ == "__main__":
    unittest.main()
