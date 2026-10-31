import os
import shutil
import tempfile
import unittest

from PIL import Image

from tools.longform import upscale


class UpscaleTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_command(self):
        c = upscale.command("/in.png", "/out.png", 4)
        self.assertEqual(c[0], upscale.BIN)
        self.assertEqual(c[c.index("-n") + 1], "realesr-animevideov3")
        self.assertEqual(c[c.index("-s") + 1], "4")

    def test_cover_box(self):
        # 16:9-ish source covering 2816x1584: scale to cover, centre-crop the rest
        self.assertEqual(upscale.cover_box((5504, 3072), (2816, 1584)), ((2838, 1584), (11, 0, 2827, 1584)))

    @unittest.skipUnless(os.path.exists(upscale.BIN), "Real-ESRGAN binary not installed")
    def test_background_size(self):
        src = os.path.join(self.d, "bg.png")
        Image.new("RGB", (688, 384), (120, 160, 90)).save(src)
        out = os.path.join(self.d, "bg_up.png")
        self.assertEqual(upscale.upscale(src, out, size=upscale.BG_SIZE), upscale.BG_SIZE)
        self.assertEqual(Image.open(out).size, (2816, 1584))

    @unittest.skipUnless(os.path.exists(upscale.BIN), "Real-ESRGAN binary not installed")
    def test_scale_keeps_aspect(self):
        src = os.path.join(self.d, "hero.png")
        Image.new("RGB", (300, 200), (0, 177, 64)).save(src)
        out = os.path.join(self.d, "hero_up.png")
        self.assertEqual(upscale.upscale(src, out, scale=2), (600, 400))


if __name__ == "__main__":
    unittest.main()
