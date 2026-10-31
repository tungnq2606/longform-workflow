import json
import os
import shutil
import tempfile
import unittest


class ImagegenTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.environ["LONGFORM_ROOT"] = self.root
        from tools.longform import imagegen, stage
        self.imagegen, self.stage = imagegen, stage

    def tearDown(self):
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def test_agy_task_lists_refs_and_name(self):
        t = self.imagegen.agy_task("PROMPT", ["/a.png", "/b.png"], "spike_bg01", "16:9")
        self.assertIn('"/a.png", "/b.png"', t)
        self.assertIn("spike_bg01", t)
        self.assertIn("16:9", t)
        self.assertIn("<PROMPT>\nPROMPT\n</PROMPT>", t)

    def test_agy_task_without_refs(self):
        self.assertNotIn("ImagePaths", self.imagegen.agy_task("P", [], "n", "16:9"))

    def test_stage_copies_only_listed(self):
        kdir = os.path.join(self.root, "library", "characters", "hero-x")
        os.makedirs(kdir)
        with open(os.path.join(kdir, "kit.json"), "w") as f:
            json.dump({"id": "hero-x"}, f)
        pdir = os.path.join(self.root, "projects", "000-spike")
        os.makedirs(pdir)
        pub = self.stage.stage(pdir, ["library/characters/hero-x"])
        self.assertEqual(pub, os.path.join(pdir, "public"))
        self.assertTrue(os.path.exists(os.path.join(pub, "library/characters/hero-x/kit.json")))
        self.assertFalse(os.path.exists(os.path.join(pub, "projects")))

    def test_stage_refuses_outside_paths(self):
        pdir = os.path.join(self.root, "projects", "000-spike")
        os.makedirs(pdir)
        with self.assertRaises(ValueError):
            self.stage.stage(pdir, ["../etc"])


if __name__ == "__main__":
    unittest.main()
