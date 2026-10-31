import json
import os
import shutil

from PIL import Image

from tools.longform.tests.imgfix import WS, bg_spec, pose_spec, prop_spec
from tools.longform.tests.test_workers import Base, script_doc


class ShotlistTest(Base):
    def setUp(self):
        super().setUp()
        lib = os.path.join(self.root, "library")
        os.makedirs(os.path.join(lib, "style"))
        shutil.copy(os.path.join(WS, "library", "style", "longform_v1.json"), os.path.join(lib, "style"))
        kdir = os.path.join(lib, "characters", "hero-a")
        os.makedirs(kdir)
        st = Image.new("RGBA", (120, 300), (0, 0, 0, 0))
        st.paste((200, 30, 30, 255), (20, 20, 100, 290))
        st.save(os.path.join(kdir, "stand_calm.png"))
        json.dump({"id": "hero-a", "name": "Hero A", "height": 530,
                   "images": {"stand.calm": {"file": "stand_calm.png", "anchor": [60, 289], "size": [120, 300]}}},
                  open(os.path.join(kdir, "kit.json"), "w"))
        os.makedirs(os.path.join(lib, "backgrounds"))
        Image.new("RGB", (64, 36), (90, 140, 90)).save(os.path.join(lib, "backgrounds", "river-01.png"))
        from tools.longform import images
        self.images = images

    def approved_script(self, approved=True):
        doc = dict(script_doc(), version=1, approved=approved)
        os.makedirs(os.path.join(self.pdir, "script"), exist_ok=True)
        json.dump(doc, open(os.path.join(self.pdir, "script", "script.json"), "w"), ensure_ascii=False)

    def result(self, items):
        self.fixture({"result.json": {"items": items}})

    def test_requires_approved_script(self):
        with self.assertRaises(ValueError):
            self.jobs.enqueue("agy_shotlist", {"project": "001-a"}, "001-a", "s")
        self.approved_script(approved=False)
        with self.assertRaises(ValueError):
            self.jobs.enqueue("agy_shotlist", {"project": "001-a"}, "001-a", "s")
        self.approved_script()
        j = self.jobs.enqueue("agy_shotlist", {"project": "001-a"}, "001-a", "s")
        self.assertEqual(j["lane"], "agy")
        self.assertEqual(j["argv"][0], self.agy.AGY)
        self.assertNotIn("--dangerously-skip-permissions", j["argv"])
        run = j["params"]["run"]
        for name in ("SHOTLIST.md", "script.json", "library.json", "style.json"):
            self.assertTrue(os.path.isfile(os.path.join(run, name)), name)
        lib = json.load(open(os.path.join(run, "library.json")))
        self.assertEqual(lib["kits"], [{"id": "hero-a", "name": "Hero A", "poses": ["stand.calm"]}])
        self.assertEqual(lib["backgrounds"], ["river-01"])
        task = open(os.path.join(run, "SHOTLIST.md"), encoding="utf-8").read()
        self.assertIn("Never run shell commands", task)
        self.assertIn("must_not", task)
        self.assertIn("Remotion", task)  # crowds are never images

    def test_items_added_and_jobs_queued(self):
        self.approved_script()
        self.result([{"type": "bg", "beat": "B01", "spec": bg_spec()},
                     {"type": "prop", "beat": "B01", "spec": prop_spec()},
                     {"type": "pose", "beat": "B01", "spec": pose_spec(), "kit": "hero-a", "pose_key": "point.determined"}])
        j = self.jobs.enqueue("agy_shotlist", {"project": "001-a"}, "001-a", "s")
        self.assertEqual(self.run_job(j), "done")
        self.assertEqual([i["id"] for i in self.images.load(self.pdir)], ["BG01", "P01", "H01"])
        self.assertEqual(sorted(j["params"]["item"] for j in self.queued("agy_image")), ["BG01", "H01", "P01"])
        from tools.longform import progress
        self.assertEqual(progress.get(self.pdir)["steps"][2]["state"], "doing")

    def test_bad_spec_refuses_all(self):
        self.approved_script()
        self.result([{"type": "bg", "beat": "B01", "spec": bg_spec()},
                     {"type": "bg", "beat": "B01", "spec": bg_spec(people="a crowd of soldiers")},
                     {"type": "pose", "beat": "B01", "spec": pose_spec(), "kit": "hero-a", "pose_key": "stand.calm"},
                     {"type": "bg", "beat": "B77", "spec": bg_spec()}])
        j = self.jobs.enqueue("agy_shotlist", {"project": "001-a"}, "001-a", "s")
        self.run_job(j)
        self.assertEqual(self.images.load(self.pdir), [])
        self.assertEqual(self.queued("agy_image"), [])
        text = " ".join(i["text"] for i in self.inbox.open_items())
        self.assertIn("people", text)
        self.assertIn("stand.calm", text)  # pose already in the kit
        self.assertIn("B77", text)  # unknown beat

    def test_reuse_background_not_generated(self):
        self.approved_script()
        self.result([{"type": "bg", "beat": "B01", "spec": {"setting": "river"}, "reuse": "river-01"}])
        j = self.jobs.enqueue("agy_shotlist", {"project": "001-a"}, "001-a", "s")
        self.assertEqual(self.run_job(j), "done")
        self.assertEqual([i["state"] for i in self.images.load(self.pdir)], ["approved"])
        self.assertEqual(self.queued("agy_image"), [])

    def test_refuses_when_list_exists(self):
        self.approved_script()
        self.images.add(self.pdir, "bg", bg_spec())
        with self.assertRaises(ValueError):
            self.jobs.enqueue("agy_shotlist", {"project": "001-a"}, "001-a", "s")
