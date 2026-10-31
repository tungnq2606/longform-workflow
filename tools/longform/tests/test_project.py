"""Project layout and language config. Run: .venv/bin/python -m unittest discover -s tools/longform/tests -v"""
import os
import shutil
import tempfile
import unittest

WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class ProjectTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "config"))
        shutil.copy(os.path.join(WS, "config", "languages.json"), os.path.join(self.root, "config"))
        os.environ["LONGFORM_ROOT"] = self.root
        from tools.longform import languages, project
        self.languages, self.project = languages, project

    def tearDown(self):
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def test_slug_ascii(self):
        self.assertEqual(self.project.ascii_slug("Bạch Đằng 1288!"), "bach-dang-1288")

    def test_create_layout(self):
        d = self.project.create_project(1, "bach-dang", "Bạch Đằng", ["en", "ja"])
        self.assertTrue(d.endswith("001-bach-dang"))
        meta = self.project.load_project(d)
        self.assertEqual(meta["languages"], ["vi", "en", "ja"])
        self.assertEqual(meta["source_lang"], "vi")
        for c in ("vi", "en", "ja"):
            self.assertTrue(os.path.isdir(os.path.join(d, "lang", c, "audio")))
        self.assertTrue(os.path.isdir(os.path.join(d, "images", "raw")))

    def test_create_slugifies(self):
        d = self.project.create_project(4, "Bạch Đằng 1288", "X", [])
        self.assertTrue(d.endswith("004-bach-dang-1288"))

    def test_unknown_language(self):
        with self.assertRaises(ValueError):
            self.project.create_project(2, "x", "X", ["fr"])

    def test_duplicate_number(self):
        self.project.create_project(3, "a", "A", [])
        with self.assertRaises(FileExistsError):
            self.project.create_project(3, "b", "B", [])

    def test_list_projects(self):
        self.project.create_project(5, "e", "E", ["de"])
        self.assertEqual([p["id"] for p in self.project.list_projects()], ["005-e"])

    def test_languages_loaded(self):
        L = self.languages.load_languages()
        self.assertEqual(set(L), {"vi", "en", "ja", "de", "es"})
        self.assertEqual(L["vi"].speed, 1.13)
        self.assertEqual(L["ja"].font, "Noto Sans JP")


if __name__ == "__main__":
    unittest.main()
