import json
import os
import shutil
import tempfile
import unittest

from PIL import Image

from tools.longform.tests.imgs import figure


class KitTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.environ["LONGFORM_ROOT"] = self.root
        from tools.longform import kit
        self.kit = kit
        self.raw = figure(os.path.join(self.root, "raw.png"))
        self.raw_blink = figure(os.path.join(self.root, "raw_blink.png"), eyes_closed=True)
        self.kdir = os.path.join(self.root, "library", "characters", "hero-x")

    def tearDown(self):
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def test_add_and_validate(self):
        probs = self.kit.add_image("hero-x", "stand.calm", self.raw, blink_src=self.raw_blink, name="Hero X", height=620)
        self.assertEqual(probs, [])
        k = self.kit.load_kit("hero-x")
        self.assertEqual(k["name"], "Hero X")
        self.assertIn("anchor", k["images"]["stand.calm"])
        self.assertEqual(k["images"]["stand.calm"]["blink"], "stand_calm_blink.png")

    def test_missing_image_file(self):
        self.kit.add_image("hero-x", "stand.calm", self.raw, name="Hero X", height=620)
        os.remove(os.path.join(self.kdir, "stand_calm.png"))
        self.assertTrue(any("missing" in p for p in self.kit.validate_kit(self.kdir)))

    def test_blink_size_mismatch(self):
        self.kit.add_image("hero-x", "stand.calm", self.raw, blink_src=self.raw_blink, name="Hero X", height=620)
        b = os.path.join(self.kdir, "stand_calm_blink.png")
        im = Image.open(b)
        im.crop((0, 0, im.size[0] - 10, im.size[1])).save(b)
        self.assertTrue(any("blink" in p for p in self.kit.validate_kit(self.kdir)))

    def test_missing_keys(self):
        os.makedirs(self.kdir)
        with open(os.path.join(self.kdir, "kit.json"), "w") as f:
            json.dump({"id": "hero-x"}, f)
        probs = self.kit.validate_kit(self.kdir)
        self.assertTrue(any("height" in p for p in probs))

    def test_write_ts_lists_keys(self):
        self.kit.add_image("hero-x", "stand.calm", self.raw, name="Hero X", height=620)
        out = os.path.join(self.root, "kits.generated.ts")
        self.kit.write_ts(out)
        with open(out, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("'hero-x/stand.calm'", src)
        self.assertIn("export const KITS", src)

    def test_write_ts_no_kits(self):
        out = os.path.join(self.root, "kits.generated.ts")
        self.kit.write_ts(out)
        with open(out, encoding="utf-8") as f:
            self.assertIn("export type HeroKey = never", f.read())


if __name__ == "__main__":
    unittest.main()
