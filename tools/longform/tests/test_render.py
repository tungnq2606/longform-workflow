import subprocess
import unittest
from unittest import mock

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

    def test_type_check_runs_before_remotion(self):
        calls = []

        def run(cmd, cwd=None, **kw):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 2 if "tsc" in cmd else 0)

        with mock.patch.object(render.subprocess, "run", run), mock.patch.object(render.stage, "stage", lambda p, f: "/pub"):
            with self.assertRaisesRegex(RuntimeError, "type check failed"):
                render.render("projects/x", "Spike", "/tmp/x.mp4", [])
        self.assertEqual(calls[0][-3:], ["-m", "tools.longform.kit", "ts"])
        self.assertIn("tsc", calls[1])
        self.assertFalse(any("remotion" in c for c in calls))  # never reached the long render


if __name__ == "__main__":
    unittest.main()
