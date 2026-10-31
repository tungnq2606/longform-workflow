import json
import os
import shutil
import tempfile
import unittest

WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def bg_spec(**kw):
    s = {"shot": "wide establishing shot", "angle": "eye level", "layout": "river across the lower third, path from left edge",
         "setting": "Bạch Đằng river mouth, 1288, low tide, mangrove banks", "people": "none",
         "props": ["wooden stakes, each as tall as two men, in rows across the river"], "light": "overcast morning",
         "must_not": ["boats with sails"]}
    s.update(kw)
    return s


def pose_spec(**kw):
    s = {"shot": "full body", "angle": "eye level", "layout": "figure centred, feet near the bottom edge",
         "setting": "plain chroma green", "people": "Trần Hưng Đạo pointing forward with his right arm",
         "props": ["sword in a scabbard at the left hip, as long as his leg"], "light": "flat even light",
         "must_not": ["helmet"]}
    s.update(kw)
    return s


class ImgSpecTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.environ["LONGFORM_ROOT"] = self.root
        os.makedirs(os.path.join(self.root, "library", "style"))
        shutil.copy(os.path.join(WS, "library", "style", "longform_v1.json"), os.path.join(self.root, "library", "style"))
        os.makedirs(os.path.join(self.root, "library", "lessons"))
        self.lessons_file = os.path.join(self.root, "library", "lessons", "prompt_lessons.json")
        json.dump({"lessons": [
            {"id": "tide", "target": "image", "when": ["tide", "submerged"], "rule": "Keep stakes under water at high tide.",
             "count": 2, "examples": [], "added": "2026-10-28"},
            {"id": "boats", "target": "image", "when": ["boat"], "rule": "Rowers grip oars.", "count": 5, "examples": [],
             "added": "2026-10-28"},
            {"id": "any", "target": "image", "when": [], "rule": "No modern objects.", "count": 1, "examples": [],
             "added": "2026-10-28"},
            {"id": "clip", "target": "clip", "when": [], "rule": "Camera moves slowly.", "count": 9, "examples": [],
             "added": "2026-10-28"}]}, open(self.lessons_file, "w"))
        from tools.longform import imgspec, lessons
        self.spec, self.lessons = imgspec, lessons

    def tearDown(self):
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def test_validate_missing_and_vague(self):
        s = bg_spec(light="dramatic sunset", layout="")
        del s["angle"]
        probs = self.spec.validate(s, "bg")
        self.assertTrue(any("angle" in p for p in probs), probs)
        self.assertTrue(any("layout" in p for p in probs), probs)
        self.assertTrue(any("dramatic" in p for p in probs), probs)
        self.assertEqual(self.spec.validate(bg_spec(), "bg"), [])
        self.assertTrue(any("must_not" in p for p in self.spec.validate(bg_spec(must_not="boats"), "bg")))
        self.assertTrue(any("a few" in p for p in self.spec.validate(bg_spec(props=["a few baskets"]), "bg")))
        self.assertEqual(self.spec.validate(bg_spec(setting="handsome temple"), "bg"), [])  # "some" only as a word
        self.assertTrue(self.spec.validate(bg_spec(), "scene"))

    def test_bg_people_must_be_none(self):
        probs = self.spec.validate(bg_spec(people="two fishermen"), "bg")
        self.assertTrue(any("people" in p for p in probs), probs)
        self.assertEqual(self.spec.validate(pose_spec(), "pose"), [])

    def test_render_includes_style_and_must(self):
        style = json.load(open(os.path.join(self.root, "library", "style", "longform_v1.json")))
        text = self.spec.render(bg_spec(), "bg")
        self.assertIn(style["background"], text)
        self.assertIn("Shot: wide establishing shot", text)
        self.assertIn("Props: wooden stakes, each as tall as two men", text)
        self.assertIn("MUST NOT:", text)
        self.assertIn("boats with sails", text)
        self.assertIn(style["negative"], text)
        self.assertIn("MUST:", text)
        self.assertIn("Keep stakes under water at high tide.", text)  # keyword "tide" in the spec
        self.assertIn("No modern objects.", text)  # no keywords: always
        self.assertNotIn("Rowers grip oars.", text)
        self.assertNotIn("Camera moves slowly.", text)
        self.assertNotIn("Exactly one figure", text)

    def test_pose_render_single_figure(self):
        style = json.load(open(os.path.join(self.root, "library", "style", "longform_v1.json")))
        text = self.spec.render(pose_spec(), "pose")
        self.assertIn(style["character"], text)
        self.assertNotIn(style["background"], text)
        self.assertIn("Exactly one figure. Full body, feet visible. Plain flat chroma green #00B140 background. Portrait framing.", text)

    def test_lessons_rules_for_keyword(self):
        self.assertEqual(self.lessons.path(), self.lessons_file)
        self.assertEqual(self.lessons.rules_for("Two BOATS at high TIDE"),
                         ["Rowers grip oars.", "Keep stakes under water at high tide.", "No modern objects."])
        self.assertEqual(self.lessons.rules_for("a temple"), ["No modern objects."])
        self.assertEqual(self.lessons.rules_for("boat", target="clip"), ["Camera moves slowly."])
        self.assertEqual(len(self.lessons.rules_for("boat tide", limit=2)), 2)

    def test_lessons_add_dedupes(self):
        self.lessons.add(["Có người trong nền.", "Có chữ trên biển hiệu"], "001-a/BG01")
        self.lessons.add(["có  người trong nền"], "001-a/BG02")
        data = json.load(open(self.lessons_file))["lessons"]
        new = [l for l in data if l["rule"].lower().startswith("có người")]
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0]["count"], 2)
        self.assertEqual(new[0]["examples"], ["001-a/BG01", "001-a/BG02"])
        self.assertEqual(new[0]["target"], "image")
        self.assertEqual(new[0]["when"], [])
        self.assertTrue(new[0]["id"] and new[0]["added"])
        self.assertEqual(len(data), 6)
        self.lessons.add([], "001-a/BG03")
        self.lessons.add(["  "], "001-a/BG03")
        self.assertEqual(len(json.load(open(self.lessons_file))["lessons"]), 6)


if __name__ == "__main__":
    unittest.main()
