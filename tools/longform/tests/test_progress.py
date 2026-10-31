import os
import shutil
import subprocess
import sys
import tempfile
import threading
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

    def test_concurrent_updates_keep_every_key(self):
        """Threads and other processes update project.json at once: no update is lost, no shared temp file breaks."""
        code = ("import sys; from tools.longform import progress\n"
                "for _ in range(40):\n"
                "    progress.set_lang(sys.argv[1], sys.argv[2], sys.argv[3], 'done')\n")
        procs = [subprocess.Popen([sys.executable, "-c", code, self.d, lang, part], cwd=WS, env=dict(os.environ),
                                  stderr=subprocess.PIPE, text=True)
                 for lang in ("en", "ja") for part in ("script", "voice")]
        errors = []

        def steps(step):
            try:
                for _ in range(40):
                    self.progress.set_step(self.d, step, "done")
            except Exception as e:  # noqa: BLE001
                errors.append(e)
        threads = [threading.Thread(target=steps, args=(st,)) for st in ("topic", "script", "images", "scenes", "render")]
        for t in threads:
            t.start()
        self.project.add_language(self.d, "de")
        for t in threads:
            t.join()
        for p in procs:
            self.assertEqual(p.wait(60), 0, p.stderr.read())
        self.assertEqual(errors, [])
        g = self.progress.get(self.d)
        self.assertEqual({s["id"] for s in g["steps"] if s["state"] == "done"}, {"topic", "script", "images", "scenes", "render"})
        langs = {l["code"]: l["parts"] for l in g["langs"]}
        for lang in ("en", "ja"):
            self.assertEqual((langs[lang]["script"], langs[lang]["voice"]), ("done", "done"))
        self.assertIn("de", self.project.load_project(self.d)["languages"])
        self.assertFalse([f for f in os.listdir(self.d) if f.endswith(".tmp") or f.startswith("tmp")])

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
