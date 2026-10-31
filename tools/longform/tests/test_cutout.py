import os
import shutil
import tempfile
import unittest

from PIL import Image, ImageDraw

from tools.longform import cutout
from tools.longform.tests.imgs import figure


class CutoutTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.dst = os.path.join(self.d, "out.png")

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_white_clothes_kept(self):
        src = figure(os.path.join(self.d, "src.png"))
        info = cutout.cut(src, self.dst)
        im = Image.open(self.dst)
        self.assertEqual(im.mode, "RGBA")
        body = im.getpixel((info["width"] // 2, info["anchor"][1] - 100))  # white body below the red belt
        self.assertEqual(body[3], 255)
        self.assertGreater(min(body[:3]), 230)
        self.assertEqual(cutout.check(self.dst, source=src), [])

    def test_key_from_border(self):
        src = figure(os.path.join(self.d, "src.png"), bg=(20, 190, 80))
        info = cutout.cut(src, self.dst)
        self.assertEqual(info["key"], [20, 190, 80])
        self.assertEqual(Image.open(self.dst).getpixel((0, 0))[3], 0)

    def test_rejects_non_green_background(self):
        src = figure(os.path.join(self.d, "src.png"), bg=(245, 240, 230))  # generator ignored the chroma prompt
        with self.assertRaisesRegex(ValueError, "not chroma green"):
            cutout.cut(src, self.dst)

    def test_green_clothing_inside_figure_kept(self):
        src = figure(os.path.join(self.d, "src.png"))
        im = Image.open(src)
        ImageDraw.Draw(im).rectangle([460, 650, 540, 700], fill=(20, 120, 50))  # dark green sash on the body
        im.save(src)
        info = cutout.cut(src, self.dst)
        x0, y0 = info["box"][:2]
        self.assertEqual(Image.open(self.dst).getpixel((500 - x0, 675 - y0))[3], 255)

    def test_enclosed_key_hole_removed(self):
        src = figure(os.path.join(self.d, "src.png"))
        im = Image.open(src)
        ImageDraw.Draw(im).rectangle([460, 650, 540, 700], fill=(0, 177, 64))  # background seen through an arm loop
        im.save(src)
        info = cutout.cut(src, self.dst)
        x0, y0 = info["box"][:2]
        self.assertEqual(Image.open(self.dst).getpixel((500 - x0, 675 - y0))[3], 0)

    def test_anchor_at_feet(self):
        src = figure(os.path.join(self.d, "src.png"), cx=500, bottom=900, width=200)
        info = cutout.cut(src, self.dst, pad=16)
        self.assertAlmostEqual(info["anchor"][0], info["width"] / 2, delta=3)
        self.assertEqual(info["anchor"][1], info["height"] - 1 - 16)

    def test_touches_edge(self):
        src = figure(os.path.join(self.d, "src.png"), through_bottom=True)
        cutout.cut(src, self.dst)
        self.assertIn("touches edge", cutout.check(self.dst, source=src))

    def test_no_transparency(self):
        p = os.path.join(self.d, "flat.png")
        Image.new("RGBA", (50, 50), (10, 10, 10, 255)).save(p)
        self.assertIn("no transparency", cutout.check(p))

    def test_key_left_on_figure(self):
        src = figure(os.path.join(self.d, "src.png"))
        cutout.cut(src, self.dst)
        im = Image.open(self.dst).convert("RGBA")
        w, h = im.size
        for x in range(w // 2 - 40, w // 2 + 40):
            for y in range(h // 2 - 40, h // 2 + 40):
                im.putpixel((x, y), (0, 177, 64, 255))
        im.save(self.dst)
        self.assertTrue(any(p.startswith("key colour left") for p in cutout.check(self.dst)))


if __name__ == "__main__":
    unittest.main()
