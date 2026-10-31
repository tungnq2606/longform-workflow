"""Shared setup for the image tests (Plan 4): a temp root with config, style lock, lessons, one hero kit, one library
background and one project. Never calls agy, Real-ESRGAN or Telegram."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from PIL import Image


WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def bg_spec(**kw):
    s = {"shot": "wide establishing shot", "angle": "eye level", "layout": "river across the lower third, path from left edge",
         "setting": "Bạch Đằng river mouth, 1288, low tide", "people": "none",
         "props": ["wooden stakes, each as tall as two men"], "light": "overcast morning", "must_not": ["boats with sails"]}
    s.update(kw)
    return s


def pose_spec(**kw):
    s = {"shot": "full body", "angle": "eye level", "layout": "figure centred", "setting": "plain chroma green",
         "people": "the hero pointing forward with his right arm", "props": ["sword at the hip, as long as his leg"],
         "light": "flat even light", "must_not": ["helmet"]}
    s.update(kw)
    return s


def prop_spec(**kw):
    s = bg_spec(shot="close-up", setting="a wooden table", props=["a bronze seal as big as a fist"])
    s.update(kw)
    return s


class ImgBase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.environ["LONGFORM_ROOT"] = self.root
        os.makedirs(os.path.join(self.root, "config"))
        for f in ("languages.json", "studio.json"):
            shutil.copy(os.path.join(WS, "config", f), os.path.join(self.root, "config"))
        lib = os.path.join(self.root, "library")
        os.makedirs(os.path.join(lib, "style"))
        shutil.copy(os.path.join(WS, "library", "style", "longform_v1.json"), os.path.join(lib, "style"))
        os.makedirs(os.path.join(lib, "lessons"))
        with open(os.path.join(lib, "lessons", "prompt_lessons.json"), "w") as f:
            json.dump({"lessons": []}, f)
        kdir = os.path.join(lib, "characters", "hero-a")
        os.makedirs(kdir)
        Image.new("RGB", (300, 200), (240, 240, 240)).save(os.path.join(kdir, "model_sheet.png"))
        stand = Image.new("RGBA", (120, 300), (0, 0, 0, 0))
        stand.paste((200, 30, 30, 255), (20, 20, 100, 290))
        stand.save(os.path.join(kdir, "stand_calm.png"))
        with open(os.path.join(kdir, "kit.json"), "w") as f:
            json.dump({"id": "hero-a", "name": "Hero A", "height": 530, "model_sheet": "model_sheet.png",
                       "images": {"stand.calm": {"file": "stand_calm.png", "anchor": [60, 289], "size": [120, 300]}}}, f)
        os.makedirs(os.path.join(lib, "backgrounds"))
        Image.new("RGB", (2816, 1584), (90, 140, 90)).save(os.path.join(lib, "backgrounds", "river-01.png"))
        from tools.longform import images, inbox, jobs, project
        self.images, self.inbox, self.jobs = images, inbox, jobs
        self.patches = [mock.patch.object(inbox.notify, "send", lambda t: True)]
        for p in self.patches:
            p.start()
        self.pdir = project.create_project(1, "a", "A", [])
        self.pid = "001-a"

    def tearDown(self):
        for p in self.patches:
            p.stop()
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def step(self):
        from tools.longform import progress
        return {s["id"]: s["state"] for s in progress.get(self.pdir)["steps"]}["images"]
