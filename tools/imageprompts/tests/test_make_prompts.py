"""Offline tests for make_prompts.py: the style lock and the other rules must hold for every prompt.

Run: python3 -m unittest discover -s tools/imageprompts/tests
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "make_prompts.py")
EXAMPLE = os.path.join(os.path.dirname(HERE), "examples", "001-hook", "images")
sys.path.insert(0, os.path.dirname(HERE))
import make_prompts as mp  # noqa: E402


class MakePromptsTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.dir, "images"))
        self.cast = json.load(open(os.path.join(EXAMPLE, "cast.json")))
        self.shots = json.load(open(os.path.join(EXAMPLE, "shots.json")))

    def tearDown(self):
        shutil.rmtree(self.dir)

    def run_tool(self, cast=None, shots=None, *args):
        json.dump(cast or self.cast, open(os.path.join(self.dir, "images", "cast.json"), "w"))
        json.dump(shots or self.shots, open(os.path.join(self.dir, "images", "shots.json"), "w"))
        return subprocess.run([sys.executable, TOOL, self.dir] + list(args), capture_output=True, text=True)

    def test_valid_example_every_prompt_has_style(self):
        p = self.run_tool()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        st = mp.load_style("stickman-v1")
        out = os.path.join(self.dir, "images", "prompts")
        txts = [f for f in os.listdir(out) if f.endswith(".txt")]
        self.assertEqual(len(txts), 18)
        for f in txts:
            self.assertIn(st["style"], open(os.path.join(out, f)).read(), f)

    def test_every_used_pose_is_on_the_cast_sheet(self):
        self.run_tool()
        man = json.load(open(os.path.join(self.dir, "images", "prompts", "manifest.json")))
        on_sheet = {tuple(k) for i in man["items"] if i["kind"] == "cast_sheet" for k in i["poses"]}
        for sh in self.shots["shots"]:
            for c in sh["characters"]:
                self.assertIn((c["name"], c["pose"]), on_sheet)

    def test_unknown_pose_is_an_error(self):
        shots = copy.deepcopy(self.shots)
        shots["shots"][0]["characters"][0]["pose"] = "moonwalk"
        p = self.run_tool(shots=shots)
        self.assertEqual(p.returncode, 1)
        self.assertIn("unknown pose", p.stdout)

    def test_third_party_brand_words_are_refused(self):
        cast = copy.deepcopy(self.cast)
        cast["characters"][0]["card"] += " In the TRUE STICKMAN style."
        p = self.run_tool(cast=cast)
        self.assertEqual(p.returncode, 1)
        self.assertIn("forbidden term", p.stdout)

    def test_too_many_named_characters_in_one_scene(self):
        shots = copy.deepcopy(self.shots)
        c = shots["shots"][0]["characters"][0]
        shots["shots"][0]["characters"] = [dict(c) for _ in range(5)]
        p = self.run_tool(shots=shots)
        self.assertEqual(p.returncode, 1)
        self.assertIn("named characters", p.stdout)

    def test_hand_edited_prompt_without_style_fails_check(self):
        self.run_tool()
        f = os.path.join(self.dir, "images", "prompts", "005_01-01.txt")
        open(f, "w").write("a man waving")
        p = self.run_tool(None, None, "--check")
        self.assertEqual(p.returncode, 1)
        self.assertIn("STYLE block missing", p.stdout)

    def test_output_is_deterministic(self):
        self.run_tool()
        a = open(os.path.join(self.dir, "images", "prompts", "prompts.md")).read()
        self.run_tool()
        b = open(os.path.join(self.dir, "images", "prompts", "prompts.md")).read()
        self.assertEqual(a, b)

    def test_cast_sheet_is_composed_never_generated(self):
        self.run_tool()
        man = json.load(open(os.path.join(self.dir, "images", "prompts", "manifest.json")))
        sheets = [i for i in man["items"] if i["kind"] == "cast_sheet"]
        self.assertEqual(len(sheets), 1)
        self.assertEqual(sheets[0]["route"], "compose")
        self.assertEqual(sheets[0]["refs"], ["refs/sheet_%s.png" % n.lower() for n in sheets[0]["characters"]])
        txt = open(os.path.join(self.dir, "images", sheets[0]["prompt_file"])).read()
        self.assertTrue(txt.startswith("DO NOT GENERATE"))

    def test_character_without_model_sheet_is_an_error(self):
        cast = copy.deepcopy(self.cast)
        for c in cast["characters"]:
            if c["name"] == "PAY":
                del c["model_sheet"]
        p = self.run_tool(cast=cast)
        self.assertEqual(p.returncode, 1)
        self.assertIn("PAY is in scenes but has no model sheet", p.stdout)

    def test_used_pose_missing_from_model_sheet_is_an_error(self):
        cast = copy.deepcopy(self.cast)
        for c in cast["characters"]:
            if c["name"] == "PAY":
                c["sheet_poses"] = ["running"]
        p = self.run_tool(cast=cast)
        self.assertEqual(p.returncode, 1)
        self.assertIn("missing from sheet_poses: running_tired", p.stdout)

    def test_style_can_replace_stick_figure_sheet_wording(self):
        st = dict(mp.load_style("stickman-v1"), turnaround=["front view", "back view", "left side view", "three-quarter front view"],
                  side_view="SIDE-NOTE", back_view="BACK-NOTE", expression_unit="expression portraits")
        txt = mp.model_sheet_prompt({"character": "WORKER"}, self.cast, st)
        self.assertIn("Row 1, four full-body views of WORKER", txt)
        self.assertIn("SIDE-NOTE; BACK-NOTE.", txt)
        self.assertIn("expression portraits of WORKER", txt)
        self.assertNotIn("single dot eye near the facing edge", txt)

    def test_animal_sheet_states_its_row_count(self):
        cast = copy.deepcopy(self.cast)
        cast["characters"].append({"name": "DOG", "kind": "animal", "model_sheet": True, "sheet_poses": ["running"],
                                   "card": "a small brown dog"})
        self.run_tool(cast=cast)
        out = os.path.join(self.dir, "images", "prompts")
        txt = open(os.path.join(out, [f for f in os.listdir(out) if f.endswith("_sheet_dog.txt")][0])).read()
        self.assertIn("exactly two rows", txt)
        self.assertIn("No people, human heads or expression circles", txt)

    def test_reference_limit(self):
        self.run_tool()
        man = json.load(open(os.path.join(self.dir, "images", "prompts", "manifest.json")))
        for i in man["items"]:
            if i["route"] != "compose":  # a composed sheet attaches nothing to a generation
                self.assertLessEqual(len(i["refs"]), 3, i["id"])


if __name__ == "__main__":
    unittest.main()
