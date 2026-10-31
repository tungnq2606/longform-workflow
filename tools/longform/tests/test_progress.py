import os
import shutil
import tempfile
import unittest

WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class ProgressTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "config"))
        shutil.copy(os.path.join(WS, "config", "languages.json"), os.path.join(self.root, "config"))
        os.environ["LONGFORM_ROOT"] = self.root
        from tools.longform import progress, project
        self.progress, self.project = progress, project
        self.d = project.create_project(1, "a", "A", ["en", "ja"])

    def tearDown(self):
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def test_default_todo(self):
        g = self.progress.get(self.d)
        self.assertEqual([s["id"] for s in g["steps"]], ["topic", "script", "images", "scenes", "langs", "render", "upload"])
        self.assertEqual({s["state"] for s in g["steps"]}, {"todo"})
        self.assertEqual((g["done"], g["total"]), (0, 7))

    def test_set_step_roundtrip(self):
        self.progress.set_step(self.d, "script", "wait")
        self.assertEqual(self.progress.get(self.d)["steps"][1], {"id": "script", "label": "Kịch bản", "state": "wait"})
        self.assertEqual(self.project.load_project(self.d)["title"], "A")  # other keys kept

    def test_set_step_unknown_raises(self):
        with self.assertRaises(ValueError):
            self.progress.set_step(self.d, "music", "done")
        with self.assertRaises(ValueError):
            self.progress.set_step(self.d, "script", "finished")
        with self.assertRaises(ValueError):
            self.progress.set_lang(self.d, "de", "voice", "done")  # project has no de
        with self.assertRaises(ValueError):
            self.progress.set_lang(self.d, "en", "music", "done")

    def test_lang_strip_follows_languages(self):
        self.progress.set_lang(self.d, "ja", "voice", "doing")
        langs = self.progress.get(self.d)["langs"]
        self.assertEqual([l["code"] for l in langs], ["vi", "en", "ja"])
        self.assertEqual(langs[2]["parts"], {"script": "todo", "voice": "doing", "render": "todo"})

    def test_done_count(self):
        self.progress.set_step(self.d, "topic", "done")
        self.progress.set_step(self.d, "script", "done")
        self.assertEqual(self.progress.get(self.d)["done"], 2)

    def test_next_number_twice(self):
        a = self.project.new_project("Bạch Đằng", [])
        b = self.project.new_project("Bạch Đằng", ["en"])
        self.assertEqual([os.path.basename(a), os.path.basename(b)], ["002-bach-dang", "003-bach-dang"])

    def test_next_number_counts_zero(self):
        shutil.rmtree(self.d)
        os.makedirs(os.path.join(self.root, "projects", "000-spike"))
        self.assertEqual(self.project.next_number(), 1)

    def test_new_project_empty_slug_raises(self):
        with self.assertRaises(ValueError):
            self.project.new_project("白藤江", [])


if __name__ == "__main__":
    unittest.main()
