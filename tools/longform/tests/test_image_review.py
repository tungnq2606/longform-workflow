import json
import os
import stat
import unittest
from unittest import mock

from PIL import Image

from tools.longform.tests.imgfix import ImgBase, bg_spec, pose_spec
from tools.longform.tests.test_workers import FAKE


class ImageReviewTest(ImgBase):
    def setUp(self):
        super().setUp()
        from tools.longform import agy, image_worker, lessons
        self.w, self.lessons = image_worker, lessons
        fake = os.path.join(self.root, "fake_agy.py")
        with open(fake, "w") as f:
            f.write(FAKE)
        os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)
        self.patches.append(mock.patch.object(agy, "AGY", fake))
        self.patches[-1].start()
        self.fix = os.path.join(self.root, "fixture")
        os.makedirs(self.fix)
        os.environ["FAKE_SRC"] = self.fix
        self.images.add(self.pdir, "bg", bg_spec())
        final = os.path.join(self.pdir, "images", "final", "BG01.png")
        os.makedirs(os.path.dirname(final))
        Image.new("RGB", (2816, 1584), (100, 120, 90)).save(final)
        self.images.update(self.pdir, "BG01", state="reviewing", files={"raw": None, "final": self.images.rel(final), "cutout": None})

    def tearDown(self):
        os.environ.pop("FAKE_SRC", None)
        super().tearDown()

    def answer(self, score, problems=(), hits=(), fix="Remove the man on the bank."):
        with open(os.path.join(self.fix, "review.json"), "w", encoding="utf-8") as f:
            json.dump({"score": score, "problems": list(problems), "must_not_hits": list(hits), "fix": fix}, f, ensure_ascii=False)

    def queued(self, kind):
        return [j for j in self.jobs.list_jobs() if j["kind"] == kind and j["status"] == "queued"]

    def test_score_5_passes(self):
        self.answer(5)
        it = self.w.review_item(self.pdir, "BG01")
        self.assertEqual((it["state"], it["score"]), ("pass", 5))
        self.assertEqual(self.inbox.open_items(), [])
        runs = os.listdir(os.path.join(self.pdir, "images", "runs"))
        self.assertEqual(len(runs), 1)
        run = os.path.join(self.pdir, "images", "runs", runs[0])
        self.assertTrue(os.path.isfile(os.path.join(run, "image.png")))
        task = open(os.path.join(run, "REVIEW.md"), encoding="utf-8").read()
        for line in self.w.RUBRIC["bg"]:
            self.assertIn(line, task)
        self.assertIn("boats with sails", task)  # the item's MUST NOT list
        self.assertIn("Never run shell commands", task)

    def test_score_3_waits_with_inbox(self):
        self.answer(3, ["Nét mực hơi nhòe"])
        it = self.w.review_item(self.pdir, "BG01")
        self.assertEqual(it["state"], "wait")
        items = self.inbox.open_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["kind"], "image_review")
        self.assertEqual(items[0]["key"], "img:001-a:BG01")
        self.assertEqual(items[0]["screen"], "images/BG01")  # the inbox line opens this image
        self.assertIn("BG01 được 3/5: Nét mực hơi nhòe", items[0]["text"])
        self.assertEqual(self.queued("agy_image"), [])

    def test_score_2_redoes(self):
        self.answer(2, ["Có người đứng trên bờ"], fix="Remove the man on the bank.")
        it = self.w.review_item(self.pdir, "BG01")
        self.assertEqual((it["state"], it["attempts"], it["fix"]), ("queued", 1, "Remove the man on the bank."))
        self.assertEqual([j["params"]["item"] for j in self.queued("agy_image")], ["BG01"])
        self.assertEqual(self.inbox.open_items(), [])

    def test_redo_capped_at_two(self):
        self.answer(2, ["Có người đứng trên bờ"])
        for _ in range(3):
            it = self.w.review_item(self.pdir, "BG01")
            if it["state"] == "queued":
                self.images.update(self.pdir, "BG01", state="reviewing")  # what the generate job does
        self.assertEqual(it["state"], "wait")
        self.assertEqual(it["attempts"], 2)
        self.assertEqual(len(self.queued("agy_image")), 2)
        self.assertTrue(any(i["key"] == "img:001-a:BG01" for i in self.inbox.open_items()))

    def test_must_not_caps_score(self):
        self.answer(5, ["Có thuyền buồm"], hits=["boats with sails"])
        it = self.w.review_item(self.pdir, "BG01")
        self.assertEqual((it["state"], it["score"]), ("wait", 3))

    def test_bad_review_waits(self):
        for bad in ({"score": 9}, {"score": "5"}, "not json"):
            with open(os.path.join(self.fix, "review.json"), "w") as f:
                f.write(bad if isinstance(bad, str) else json.dumps(bad))
            it = self.w.review_item(self.pdir, "BG01")
            self.assertEqual(it["state"], "wait")
            self.assertIn("agy không chấm được ảnh này", it["problems"])
            self.images.update(self.pdir, "BG01", state="reviewing")
        os.remove(os.path.join(self.fix, "review.json"))
        self.assertEqual(self.w.review_item(self.pdir, "BG01")["state"], "wait")

    def test_low_score_adds_lesson(self):
        self.answer(3, ["Có chữ trên lá cờ"])
        self.w.review_item(self.pdir, "BG01")
        self.assertIn("Có chữ trên lá cờ", self.lessons.rules_for("anything"))
        data = json.load(open(self.lessons.path()))["lessons"]
        self.assertEqual(data[0]["examples"], ["001-a/BG01"])
        self.images.update(self.pdir, "BG01", state="reviewing")
        self.answer(4, ["Trời hơi tối"])
        self.w.review_item(self.pdir, "BG01")
        self.assertNotIn("Trời hơi tối", self.lessons.rules_for("anything"))

    def test_pose_review_gets_refs_and_cutout(self):
        it = self.images.add(self.pdir, "pose", pose_spec(), kit="hero-a", pose_key="point.determined")
        for name in ("final", "cutout"):
            p = os.path.join(self.pdir, "images", name, "H01.png")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            Image.new("RGBA", (400, 800), (0, 177, 64, 255)).save(p)
        self.images.update(self.pdir, "H01", state="reviewing", files={
            "raw": None, "final": "projects/001-a/images/final/H01.png", "cutout": "projects/001-a/images/cutout/H01.png"})
        self.answer(5)
        self.assertEqual(self.w.review_item(self.pdir, "H01")["state"], "pass")
        run = os.path.join(self.pdir, "images", "runs", sorted(d for d in os.listdir(os.path.join(self.pdir, "images", "runs")) if "H01" in d)[0])
        self.assertEqual(sorted(os.listdir(run)), ["REVIEW.md", "cutout.png", "image.png", "ref1.png", "ref2.png", "review.json"])
        task = open(os.path.join(run, "REVIEW.md"), encoding="utf-8").read()
        self.assertIn("one figure", task)

    def test_review_quota_pauses_and_retries(self):
        os.environ["FAKE_SRC"] = ""
        with mock.patch.object(self.w.subprocess, "run", return_value=mock.Mock(stdout="", stderr="RESOURCE_EXHAUSTED quota")):
            it = self.w.review_item(self.pdir, "BG01")
        self.assertEqual(it["state"], "reviewing")
        self.assertTrue(self.jobs.paused()["on"])
        self.assertEqual([j["params"]["item"] for j in self.queued("agy_image_review")], ["BG01"])


if __name__ == "__main__":
    unittest.main()
