"""Per-language thumbnail: props from an approved background item and a kit pose, the remotion still command, the job."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image

WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class ThumbTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "config"))
        for f in ("languages.json", "studio.json"):
            shutil.copy(os.path.join(WS, "config", f), os.path.join(self.root, "config"))
        os.environ["LONGFORM_ROOT"] = self.root
        from tools.longform import images, inbox, jobs, project, render, thumb
        self.images, self.jobs, self.render, self.t = images, jobs, render, thumb
        self.p = mock.patch.object(inbox.notify, "send", lambda t: True)
        self.p.start()
        self.pdir = project.create_project(1, "a", "A", ["ja"])
        kit = os.path.join(self.root, "library", "characters", "tran-hung-dao")
        os.makedirs(kit)
        Image.new("RGBA", (40, 100)).save(os.path.join(kit, "stand_calm.png"))
        json.dump({"id": "tran-hung-dao", "name": "Trần Hưng Đạo", "height": 530,
                   "images": {"stand.calm": {"file": "stand_calm.png", "anchor": [20, 99], "size": [40, 100]}}},
                  open(os.path.join(kit, "kit.json"), "w"))
        raw = os.path.join(self.pdir, "images", "raw")
        Image.new("RGB", (160, 90)).save(os.path.join(raw, "BG01.png"))
        items = [{"id": "BG01", "type": "bg", "state": "approved", "files": {"raw": None, "final": "projects/001-a/images/raw/BG01.png",
                                                                            "cutout": None}},
                 {"id": "BG02", "type": "bg", "state": "wait", "files": {"raw": None, "final": "projects/001-a/images/raw/BG01.png",
                                                                        "cutout": None}},
                 {"id": "P01", "type": "prop", "state": "approved", "files": {"raw": None, "final": "projects/001-a/images/raw/BG01.png",
                                                                             "cutout": None}}]
        json.dump(items, open(os.path.join(self.pdir, "images", "items.json"), "w"))

    def tearDown(self):
        self.p.stop()
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def test_render_thumb_props(self):
        out = self.t.props(self.pdir, "ja", "BG01", "tran-hung-dao/stand.calm", "バクダン川の秘密")
        self.assertEqual(out["props"], {"bg": "projects/001-a/images/raw/BG01.png",
                                        "hero": "library/characters/tran-hung-dao/stand_calm.png",
                                        "title": "バクダン川の秘密", "lang": "ja"})
        self.assertIn("tools/kit/fonts/NotoSansJP-Variable.ttf", out["files"])
        self.assertIn("projects/001-a/images/raw/BG01.png", out["files"])
        self.assertEqual(out["out"], os.path.join(self.pdir, "lang", "ja", "upload", "thumb.png"))
        for bad in (("BG02", "tran-hung-dao/stand.calm", "x"),  # not approved
                    ("P01", "tran-hung-dao/stand.calm", "x"),   # not a background
                    ("BG09", "tran-hung-dao/stand.calm", "x"),
                    ("BG01", "tran-hung-dao/run.fast", "x"),    # pose not in the kit
                    ("BG01", "../x/stand.calm", "x"),
                    ("BG01", "tran-hung-dao/stand.calm", ""),
                    ("BG01", "tran-hung-dao/stand.calm", "x" * 101)):
            with self.assertRaises(ValueError):
                self.t.props(self.pdir, "ja", *bad)
        with self.assertRaises(ValueError):
            self.t.props(self.pdir, "de", "BG01", "tran-hung-dao/stand.calm", "x")  # not a project language
        cmd = self.render.command("Thumb", "/o.png", "/pub", frame=0, props=out["props"])
        self.assertEqual(cmd[:6], ["npx", "remotion", "still", "src/index.ts", "Thumb", "/o.png"])

    def test_job_kind(self):
        j = self.jobs.enqueue("render_thumb", {"project": "001-a", "lang": "ja", "bg": "BG01", "hero": "tran-hung-dao/stand.calm",
                                               "title": "バクダン川"}, "001-a", "thumbnail JA")
        self.assertEqual(j["lane"], "render")
        self.assertEqual(j["argv"][1:4], ["-m", "tools.longform.thumb", "001-a"])
        self.assertNotIn("claude", " ".join(j["argv"][1:]))
        with self.assertRaises(ValueError):
            self.jobs.enqueue("render_thumb", {"project": "001-a", "lang": "ja", "bg": "BG02", "hero": "tran-hung-dao/stand.calm",
                                               "title": "x"}, "001-a", "x")


if __name__ == "__main__":
    unittest.main()
