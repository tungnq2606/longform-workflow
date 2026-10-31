import unittest

from tools.longform import render


class RenderTest(unittest.TestCase):
    def test_video_command(self):
        c = render.command("Spike", "/o.mp4", "/pub", props={"boil": True})
        self.assertEqual(c[:4], ["npx", "remotion", "render", "src/index.ts"])
        self.assertEqual(c[4:6], ["Spike", "/o.mp4"])
        self.assertEqual(c[c.index("--public-dir") + 1], "/pub")
        self.assertIn('--props={"boil": true}', c)
        self.assertFalse(any(x.startswith("--crf") for x in c))  # remotion.config.ts sets 16M bitrate; crf conflicts

    def test_still_command(self):
        c = render.command("Spike", "/o.png", "/pub", frame=150)
        self.assertEqual(c[:3], ["npx", "remotion", "still"])
        self.assertIn("--frame=150", c)


if __name__ == "__main__":
    unittest.main()
