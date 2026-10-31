"""On-screen labels (dates, names, map places) per language, written by agy from the Vietnamese labels + glossary."""
import json
import os
import shutil
import unittest

from tools.longform.tests.test_workers import WS, Base

LABELS = {"date_1288": {"vi": "Mùa xuân 1288"}, "name_thd": {"vi": "Trần Hưng Đạo"}}


class LangLabelsTest(Base):
    def setUp(self):
        super().setUp()
        from tools.longform import langscript, scenes
        self.ls, self.scenes = langscript, scenes
        meta = json.load(open(os.path.join(self.pdir, "project.json"), encoding="utf-8"))
        meta["languages"] = ["vi", "en", "ja"]
        json.dump(meta, open(os.path.join(self.pdir, "project.json"), "w", encoding="utf-8"), ensure_ascii=False)
        lib = os.path.join(self.root, "library")
        shutil.copytree(os.path.join(WS, "library", "glossary"), os.path.join(lib, "glossary"))
        shutil.copy(os.path.join(WS, "library", "stylebook", "en.json"), os.path.join(lib, "stylebook"))
        os.makedirs(os.path.join(self.pdir, "scenes"), exist_ok=True)
        json.dump(LABELS, open(os.path.join(self.pdir, "scenes", "labels.json"), "w", encoding="utf-8"), ensure_ascii=False)

    def run_labels(self, result, lang="en"):
        self.fixture({"result.json": result})
        j = self.jobs.enqueue("agy_labels", {"project": "001-a", "lang": lang}, "001-a", "agy nhãn " + lang)
        self.assertEqual(j["argv"][0], self.agy.AGY)
        run = j["params"]["run"]
        given = json.load(open(os.path.join(run, "labels.json"), encoding="utf-8"))
        self.assertEqual(given, {"date_1288": "Mùa xuân 1288", "name_thd": "Trần Hưng Đạo"})
        self.assertTrue(os.path.isfile(os.path.join(run, "glossary.json")))
        self.run_job(j)

    def test_labels_merged_for_language(self):
        self.run_labels({"date_1288": "Spring 1288", "name_thd": "Tran Hung Dao"})
        lbl = self.scenes.own_labels(self.pdir)
        self.assertEqual(lbl["date_1288"], {"vi": "Mùa xuân 1288", "en": "Spring 1288"})
        self.assertEqual(lbl["name_thd"]["en"], "Tran Hung Dao")

    def test_missing_key_refused(self):
        self.run_labels({"date_1288": "Spring 1288"})
        self.assertNotIn("en", self.scenes.own_labels(self.pdir)["date_1288"])
        self.assertTrue(any("name_thd" in i["text"] for i in self.inbox.open_items()))

    def test_too_long_label_refused(self):
        self.run_labels({"date_1288": "x" * 200, "name_thd": "Tran Hung Dao"})
        self.assertNotIn("en", self.scenes.own_labels(self.pdir)["name_thd"])

    def test_requires_labels_file(self):
        os.remove(os.path.join(self.pdir, "scenes", "labels.json"))
        with self.assertRaises(ValueError):
            self.jobs.enqueue("agy_labels", {"project": "001-a", "lang": "en"}, "001-a", "x")

    def test_source_language_refused(self):
        with self.assertRaises(ValueError):
            self.jobs.enqueue("agy_labels", {"project": "001-a", "lang": "vi"}, "001-a", "x")


if __name__ == "__main__":
    unittest.main()
