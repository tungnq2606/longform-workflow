import json
import os
import shutil
import tempfile
import unittest

from PIL import Image

from tools.longform import library_index


class LibraryIndexTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.environ["LONGFORM_ROOT"] = self.root
        lib = os.path.join(self.root, "library")
        kdir = os.path.join(lib, "characters", "hero-a")
        os.makedirs(kdir)
        Image.new("RGBA", (300, 900), (200, 30, 30, 255)).save(os.path.join(kdir, "stand.png"))
        json.dump({"id": "hero-a", "name": "Hero A", "height": 500,
                   "images": {"stand.calm": {"file": "stand.png"}, "point.x": {"file": "point.png"}}},
                  open(os.path.join(kdir, "kit.json"), "w"))
        os.makedirs(os.path.join(lib, "backgrounds"))
        Image.new("RGB", (2816, 1584), (90, 140, 90)).save(os.path.join(lib, "backgrounds", "river-01.png"))
        os.makedirs(os.path.join(lib, "style"))
        json.dump({"id": "longform-v1", "approved": True}, open(os.path.join(lib, "style", "longform_v1.json"), "w"))

    def tearDown(self):
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def test_summary(self):
        s = library_index.summary()
        self.assertEqual(s["characters"], [{"id": "hero-a", "name": "Hero A", "poses": 2}])
        self.assertEqual(s["backgrounds"], [{"id": "river-01"}])
        self.assertEqual(s["styles"], [{"id": "longform-v1", "approved": True}])

    def test_empty_library(self):
        shutil.rmtree(os.path.join(self.root, "library"))
        self.assertEqual(library_index.summary(), {"characters": [], "backgrounds": [], "styles": []})

    def test_thumb_background(self):
        p = library_index.thumb("bg", "river-01")
        im = Image.open(p)
        self.assertEqual(im.format, "JPEG")
        self.assertEqual(im.size[0], 1600)
        self.assertEqual(library_index.thumb("bg", "river-01"), p)  # cached

    def test_thumb_character_keeps_alpha(self):
        im = Image.open(library_index.thumb("char", "hero-a"))
        self.assertEqual(im.format, "PNG")
        self.assertEqual(im.mode, "RGBA")
        self.assertEqual(im.size[1], 480)

    def test_thumb_unknown(self):
        for kind, item in (("bg", "nope"), ("char", "nope"), ("bg", "../characters/hero-a/stand"), ("x", "river-01")):
            with self.assertRaises(KeyError):
                library_index.thumb(kind, item)


if __name__ == "__main__":
    unittest.main()
