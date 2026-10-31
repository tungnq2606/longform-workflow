import os
import shutil
import unittest
from unittest import mock

from PIL import Image, ImageDraw

from tools.longform.tests.imgfix import ImgBase, bg_spec, pose_spec, prop_spec
from tools.longform.tests.imgs import figure


def scene(path, seed=0):
    """A background-like raw image at agy's usual size."""
    im = Image.new("RGB", (1376, 768), (120 + seed, 150, 110))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 600, 1376, 768], fill=(90, 70, 40))
    d.ellipse([200 + seed, 100, 400 + seed, 300], fill=(240, 220, 120))
    im.save(path)
    return path


def hero(path):
    return figure(path, size=(640, 1100), cx=320, bottom=1000)


def two_heroes(path):
    a = Image.open(figure(path, size=(600, 1100), cx=300, bottom=1000))
    im = Image.new("RGB", (1200, 1100))
    im.paste(a, (0, 0))
    im.paste(a, (600, 0))
    im.save(path)
    return path


class ImageWorkerTest(ImgBase):
    def setUp(self):
        super().setUp()
        from tools.longform import imagegen, image_worker, upscale
        self.w, self.imagegen = image_worker, imagegen
        self.calls = []
        self.maker = scene

        def fake_generate(prompt, refs, out_dir, name, aspect="16:9"):
            self.calls.append({"prompt": prompt, "refs": refs, "name": name, "aspect": aspect})
            os.makedirs(out_dir, exist_ok=True)
            return [self.maker(os.path.join(out_dir, "%s_v%d.png" % (name, len(self.calls))))]

        def fake_upscale(src, dst, size=None, scale=2):
            im = Image.open(src).convert("RGB")
            if size:
                from tools.longform.upscale import cover_box
                rs, box = cover_box(im.size, size)
                im = im.resize(rs).crop(box)
            else:
                im = im.resize((im.size[0] * scale, im.size[1] * scale))
            im.save(dst)
            return im.size

        self.patches += [mock.patch.object(imagegen, "generate", fake_generate),
                         mock.patch.object(upscale, "upscale", fake_upscale)]
        for p in self.patches[1:]:
            p.start()

    def queued(self, kind):
        return [j for j in self.jobs.list_jobs() if j["kind"] == kind and j["status"] == "queued"]

    def test_generate_bg_goes_to_review(self):
        self.images.add(self.pdir, "bg", bg_spec())
        it = self.w.generate_item(self.pdir, "BG01")
        self.assertEqual(it["state"], "reviewing")
        self.assertEqual(self.calls[0]["aspect"], "16:9")
        self.assertIn("Shot: wide establishing shot", self.calls[0]["prompt"])
        final = self.images.abspath(it["files"]["final"])
        self.assertEqual(Image.open(final).size, (2816, 1584))
        self.assertTrue(os.path.isfile(self.images.abspath(it["files"]["raw"])))
        self.assertEqual([h["event"] for h in it["history"]], ["queued", "generating", "reviewing"])
        self.assertEqual([j["params"]["item"] for j in self.queued("agy_image_review")], ["BG01"])

    def test_prop_upscaled_x2_and_fix_in_prompt(self):
        self.images.add(self.pdir, "prop", prop_spec())
        self.images.update(self.pdir, "P01", fix="Make the seal square.")
        it = self.w.generate_item(self.pdir, "P01")
        self.assertEqual(Image.open(self.images.abspath(it["files"]["final"])).size, (2752, 1536))
        self.assertIn("Make the seal square.", self.calls[0]["prompt"])

    def test_pose_cutout_and_portrait_aspect(self):
        self.maker = hero
        self.images.add(self.pdir, "pose", pose_spec(), kit="hero-a", pose_key="point.determined")
        it = self.w.generate_item(self.pdir, "H01")
        self.assertEqual(it["state"], "reviewing", it["problems"])
        self.assertEqual(self.calls[0]["aspect"], "9:16")
        self.assertEqual([os.path.basename(r) for r in self.calls[0]["refs"]], ["model_sheet.png", "stand_calm.png"])
        self.assertTrue(all(os.path.isabs(r) for r in self.calls[0]["refs"]))
        self.assertEqual(Image.open(self.images.abspath(it["files"]["final"])).size, (1280, 2200))
        cut = Image.open(self.images.abspath(it["files"]["cutout"]))
        self.assertEqual(cut.mode, "RGBA")
        self.assertEqual(cut.getpixel((0, 0))[3], 0)

    def test_multi_figure_hero_fails_check(self):
        path = two_heroes(os.path.join(self.root, "two.png"))
        item = {"id": "H01", "type": "pose"}
        probs = self.w.check_raw(item, path, self.pdir)
        self.assertTrue(any("một nhân vật" in p for p in probs), probs)
        self.assertEqual(self.w.check_raw(item, hero(os.path.join(self.root, "one.png")), self.pdir), [])
        self.maker = two_heroes
        self.images.add(self.pdir, "pose", pose_spec(), kit="hero-a", pose_key="point.determined")
        it = self.w.generate_item(self.pdir, "H01")
        self.assertEqual(it["state"], "queued")  # never reaches review
        self.assertEqual(it["attempts"], 1)
        self.assertIn("one figure", it["fix"])
        self.assertEqual(self.queued("agy_image_review"), [])
        self.assertEqual([j["params"]["item"] for j in self.queued("agy_image")], ["H01"])

    def test_check_fails_three_times_waits_for_owner(self):
        self.maker = two_heroes
        self.images.add(self.pdir, "pose", pose_spec(), kit="hero-a", pose_key="point.determined")
        for _ in range(3):
            it = self.w.generate_item(self.pdir, "H01")
        self.assertEqual(it["state"], "wait")
        self.assertEqual(it["attempts"], 3)
        self.assertTrue(any(i["key"] == "img:001-a:H01" for i in self.inbox.open_items()))

    def test_small_and_not_green(self):
        small = os.path.join(self.root, "small.png")
        Image.new("RGB", (800, 450), (100, 100, 100)).save(small)
        self.assertTrue(any("nhỏ" in p for p in self.w.check_raw({"id": "BG01", "type": "bg"}, small, self.pdir)))
        grey = scene(os.path.join(self.root, "grey.png"))
        self.assertTrue(any("xanh" in p for p in self.w.check_raw({"id": "H01", "type": "pose"}, grey, self.pdir)))

    def test_duplicate_fails_check(self):
        self.images.add(self.pdir, "bg", bg_spec())
        self.images.add(self.pdir, "bg", bg_spec())
        self.w.generate_item(self.pdir, "BG01")
        it = self.w.generate_item(self.pdir, "BG02")  # the fake draws the same picture again
        self.assertEqual(it["state"], "queued")
        self.assertTrue(any("trùng" in p and "BG01" in p for p in it["problems"]), it["problems"])

    def test_quota_pauses_and_requeues(self):
        self.images.add(self.pdir, "bg", bg_spec())

        def no_quota(*a, **kw):
            raise self.imagegen.QuotaExhausted("RESOURCE_EXHAUSTED")

        with mock.patch.object(self.imagegen, "generate", no_quota):
            it = self.w.generate_item(self.pdir, "BG01")
        self.assertEqual(it["state"], "queued")
        self.assertEqual(it["attempts"], 0)
        self.assertEqual(self.jobs.paused(), {"on": True, "reason": "agy hết quota", "since": self.jobs.paused()["since"]})
        self.assertTrue(any(i["kind"] == "quota" for i in self.inbox.open_items()))

    def test_quota_exit_code_zero(self):
        self.images.add(self.pdir, "bg", bg_spec())
        with mock.patch.object(self.imagegen, "generate", mock.Mock(side_effect=self.imagegen.QuotaExhausted("q"))):
            self.assertEqual(self.w.main(["generate", self.pid, "BG01"]), 0)
        self.assertEqual(self.images.get(self.pdir, "BG01")["state"], "queued")

    def test_argv_runs_python_worker_not_claude(self):
        self.images.add(self.pdir, "bg", bg_spec())
        j = self.jobs.enqueue("agy_image", {"project": self.pid, "item": "BG01"}, self.pid, "agy vẽ BG01")
        self.assertEqual(j["lane"], "agy")
        self.assertEqual(j["argv"], [os.path.join(self.w.paths.WS, ".venv", "bin", "python"), "-m",
                                     "tools.longform.image_worker", "generate", self.pid, "BG01"])
        self.assertFalse(any("claude" in a or "skip-permissions" in a for a in j["argv"]))
        r = self.jobs.enqueue("agy_image_review", {"project": self.pid, "item": "BG01"}, self.pid, "agy chấm BG01")
        self.assertEqual(r["argv"][-3:], ["review", self.pid, "BG01"])
        with self.assertRaises(ValueError):
            self.jobs.enqueue("agy_image", {"project": self.pid, "item": "BG99"}, self.pid, "x")
        with self.assertRaises(ValueError):
            self.jobs.enqueue("agy_image", {"project": "../x", "item": "BG01"}, self.pid, "x")

    def test_crashed_job_marks_item_failed(self):
        self.images.add(self.pdir, "bg", bg_spec())
        self.images.update(self.pdir, "BG01", state="generating")
        self.w.job_end({"kind": "agy_image", "status": "failed", "params": {"project": self.pid, "item": "BG01"}})
        self.assertEqual(self.images.get(self.pdir, "BG01")["state"], "failed")


if __name__ == "__main__":
    unittest.main()
