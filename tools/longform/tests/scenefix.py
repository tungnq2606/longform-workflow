"""Shared setup for the Plan 5 scene tests: Base (temp root, fake agy/claude) plus one hero kit, one library background
with geometry, an approved script, a fact bank, one approved image and a small audio library."""
import copy
import json
import os

from PIL import Image

from tools.longform.tests.test_workers import PAGE, Base, claim, script_doc


def scenes_doc():
    return {"version": 0, "chapters": [{"id": "C01", "music": "open-01", "title_card": True}], "beats": {"B01": {
        "background": {"id": "library:river-01", "camera": {"from": {"zoom": 1, "x": 0, "y": 0}, "to": {"zoom": 1.1, "x": -40, "y": 0}}},
        "heroes": [{"key": "hero-a/stand.calm", "x": 1900, "enter": "right", "keys": [{"sentence": "s002", "key": "hero-a/point.angry"}]}],
        "crowds": [{"faction": "nguyen", "count": 20, "path": "background", "speed": 0.001}],
        "cards": [{"type": "date", "sentence": "s002", "text_key": "date_1288"}],
        "map": None,
        "sfx": [{"sentence": "s002", "id": "oar-01", "offset": 0.3, "gain": 0.4}]}}}


def labels_doc():
    return {"date_1288": {"vi": "Năm 1288", "en": "1288"}, "place_bd": {"vi": "Sông Bạch Đằng"}}


def map_doc(fact=None, type="area"):
    return {"bbox": [105, 19, 109, 22], "places": [{"label_key": "place_bd", "lon": 106.8, "lat": 20.9}],
            "arrows": [{"from": [107.5, 21.0], "to": [106.8, 20.9], "sentence": "s002"}],
            "areas": [{"points": [[106.5, 20.8], [107, 20.8], [107, 21.1]], "fact": fact, "type": type}]}


class SceneBase(Base):
    def setUp(self):
        super().setUp()
        lib = os.path.join(self.root, "library")
        kdir = os.path.join(lib, "characters", "hero-a")
        os.makedirs(kdir)
        im = Image.new("RGBA", (120, 300), (0, 0, 0, 0))
        im.paste((200, 30, 30, 255), (20, 20, 100, 290))
        images = {}
        for key in ("stand.calm", "point.angry"):
            im.save(os.path.join(kdir, key.replace(".", "_") + ".png"))
            images[key] = {"file": key.replace(".", "_") + ".png", "anchor": [60, 289], "size": [120, 300]}
        with open(os.path.join(kdir, "kit.json"), "w") as f:
            json.dump({"id": "hero-a", "name": "Hero A", "height": 530, "images": images}, f)
        os.makedirs(os.path.join(lib, "backgrounds"))
        Image.new("RGB", (64, 36), (90, 140, 90)).save(os.path.join(lib, "backgrounds", "river-01.png"))
        with open(os.path.join(lib, "backgrounds", "river-01.json"), "w") as f:
            json.dump({"image": "library/backgrounds/river-01.png", "horizonY": 600, "groundY": 1440,
                       "path": [[2600, 1100], [800, 700]], "heroGround": 1320}, f)
        os.makedirs(os.path.join(lib, "audio", "music"))
        os.makedirs(os.path.join(lib, "audio", "sfx"))
        for rel in ("music/open-01.mp3", "sfx/oar-01.mp3"):
            open(os.path.join(lib, "audio", rel), "wb").close()
        with open(os.path.join(lib, "audio", "index.json"), "w") as f:
            json.dump({"music": [{"id": "open-01", "file": "music/open-01.mp3", "kind": "music", "mood": "opening", "license": "L"}],
                       "sfx": [{"id": "oar-01", "file": "sfx/oar-01.mp3", "kind": "sfx", "tags": ["oar"], "license": "L"}]}, f)
        self.seed_bank(claim("c1", "quân Nguyên đến sông Bạch Đằng", claim_vi="Năm 1288 quân Nguyên đến sông Bạch Đằng"))
        self.fact = sorted(self.fb.load(self.pdir)[1])[0]
        self.fb.set_status(self.pdir, self.fact, "verified", "test", "")
        from tools.longform import images as images_mod, scenes
        self.images, self.scenes = images_mod, scenes

    def approve_script(self, approved=True):
        doc = dict(script_doc(facts=(self.fact,)), version=1, approved=approved)
        with open(os.path.join(self.pdir, "script", "script.json"), "w") as f:
            json.dump(doc, f, ensure_ascii=False)

    def approve_image(self):
        self.images.add(self.pdir, "bg", None, reuse="river-01")

    def doc(self):
        return copy.deepcopy(scenes_doc())


__all__ = ["SceneBase", "scenes_doc", "labels_doc", "map_doc", "PAGE"]
