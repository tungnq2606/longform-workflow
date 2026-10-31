"""Per-language rewrite (agy), automatic checks and Claude language review, with the fake agy/claude of test_workers."""
import json
import os
import shutil
import unittest

from tools.longform.tests.test_workers import WS, Base, claim

SRC = {"lang": "vi", "chapters": [{"id": "C01", "title": "Mở đầu", "beats": [
    {"id": "B01", "goal": "hook: một dòng sông thắng một hạm đội", "sentences": [
        {"id": "s001", "text": "Bạn có biết chuyện này không?", "facts": [], "kind": "question", "note": ""},
        {"id": "s002", "text": "Năm 1288, quân Nguyên đến sông Bạch Đằng.", "facts": ["F001"], "kind": "fact", "note": ""}]},
    {"id": "B02", "goal": "bắt tướng giặc", "sentences": [
        {"id": "s003", "text": "Trần Hưng Đạo bắt được Ô Mã Nhi.", "facts": ["F002"], "kind": "fact", "note": ""}]}]}]}


def en_doc(b01=None, b02=None):
    b01 = b01 or [{"id": "s001", "text": "Have you ever wondered how a river can beat a fleet?", "facts": [], "kind": "question", "note": ""},
                  {"id": "s002", "text": "In 1288, the Yuan fleet sailed into the Bach Dang River.", "facts": ["F001"], "kind": "fact", "note": ""}]
    b02 = b02 or [{"id": "s003", "text": "Tran Hung Dao's men captured Omar.", "facts": ["F002"], "kind": "fact", "note": ""}]
    return {"lang": "en", "chapters": [{"id": "C01", "title": "A river against a fleet", "beats": [
        {"id": "B01", "goal": "hook", "sentences": b01}, {"id": "B02", "goal": "capture", "sentences": b02}]}]}


class LangScriptTest(Base):
    def setUp(self):
        super().setUp()
        from tools.longform import langscript, progress
        self.ls, self.progress = langscript, progress
        meta = json.load(open(os.path.join(self.pdir, "project.json"), encoding="utf-8"))
        meta["languages"] = ["vi", "en", "ja"]
        json.dump(meta, open(os.path.join(self.pdir, "project.json"), "w", encoding="utf-8"), ensure_ascii=False)
        for code in ("en", "ja"):
            for sub in ("script", "audio", "render", "upload"):
                os.makedirs(os.path.join(self.pdir, "lang", code, sub), exist_ok=True)
        lib = os.path.join(self.root, "library")
        shutil.copytree(os.path.join(WS, "library", "glossary"), os.path.join(lib, "glossary"))
        shutil.copytree(os.path.join(WS, "library", "localization"), os.path.join(lib, "localization"))
        for code in ("en", "ja"):
            shutil.copy(os.path.join(WS, "library", "stylebook", code + ".json"), os.path.join(lib, "stylebook"))
        self.seed_bank(claim("S1", "quân Nguyên đến sông Bạch Đằng", claim_vi="Năm 1288 quân Nguyên đến sông Bạch Đằng"),
                       claim("S2", "Quân ta bắt được Ô Mã Nhi", claim_vi="Quân Trần bắt được Ô Mã Nhi"))
        for fid in ("F001", "F002"):
            self.fb.set_status(self.pdir, fid, "verified", "claude", "", "A")

    def approve_source(self):
        self.script.save(self.pdir, json.loads(json.dumps(SRC)), "owner")
        self.script.approve(self.pdir, "owner")

    def rewrite(self, result):
        self.fixture({"result.json": result})
        j = self.jobs.enqueue("agy_rewrite", {"project": "001-a", "lang": "en"}, "001-a", "agy viết lại EN")
        self.assertEqual(self.run_job(j), "done")
        return j

    def row(self, check, sid):
        return [r for r in check["report"]["sentences"] if r["id"] == sid][0]

    def test_outline_has_no_source_sentences(self):
        self.approve_source()
        self.assertEqual(self.ls.outline(self.pdir), [
            {"beat": "B01", "goal": "hook: một dòng sông thắng một hạm đội", "facts": ["F001"], "chapter": "C01"},
            {"beat": "B02", "goal": "bắt tướng giặc", "facts": ["F002"], "chapter": "C01"}])
        j = self.jobs.enqueue("agy_rewrite", {"project": "001-a", "lang": "en"}, "001-a", "agy viết lại EN")
        self.assertEqual(j["argv"][0], self.agy.AGY)
        self.assertNotIn("--dangerously-skip-permissions", j["argv"])
        run = j["params"]["run"]
        for name in ("outline.json", "glossary.json", "style.md", "GUIDE.md", "REWRITE.md"):
            self.assertTrue(os.path.isfile(os.path.join(run, name)), name)
        blob = ""
        for dirpath, _, files in os.walk(run):
            for name in files:
                blob += open(os.path.join(dirpath, name), encoding="utf-8").read()
        for _, s in self.script.sentences(SRC):
            self.assertNotIn(s["text"], blob)
            self.assertNotIn(s["text"].rstrip(".?"), blob)
        outline = json.load(open(os.path.join(run, "outline.json"), encoding="utf-8"))
        self.assertEqual(outline["beats"][0]["facts"][0]["quote"], "quân Nguyên đến sông Bạch Đằng")
        self.assertEqual(outline["beats"][0]["facts"][0]["claim"], "Năm 1288 quân Nguyên đến sông Bạch Đằng")
        self.assertNotIn("sentences", json.dumps(outline))
        self.assertIn("Never run shell commands", j["argv"][2])
        rewrite_md = open(os.path.join(run, "REWRITE.md"), encoding="utf-8").read()
        self.assertIn("English", rewrite_md)
        self.assertEqual(j["params"]["base_version"], 0)

    def test_rewrite_requires_approved_source(self):
        self.script.save(self.pdir, json.loads(json.dumps(SRC)), "owner")
        with self.assertRaises(ValueError):
            self.jobs.enqueue("agy_rewrite", {"project": "001-a", "lang": "en"}, "001-a", "x")
        self.script.approve(self.pdir, "owner")
        for bad in ("vi", "de", "xx", None):
            with self.assertRaises(ValueError):
                self.jobs.enqueue("agy_rewrite", {"project": "001-a", "lang": bad}, "001-a", "x")

    def test_missing_beat_refused(self):
        self.approve_source()
        self.script.save(self.pdir, en_doc(), "agy", lang="en")
        old = self.script.load(self.pdir, "en")["version"]
        doc = en_doc()
        doc["chapters"][0]["beats"] = doc["chapters"][0]["beats"][:1]
        self.rewrite(doc)
        self.assertEqual(self.script.load(self.pdir, "en")["version"], old)
        items = [i for i in self.inbox.open_items() if i["kind"] == "job_failed"]
        self.assertEqual(len(items), 1)
        self.assertIn("B02", items[0]["text"])
        self.assertEqual(items[0]["screen"], "langs")
        self.assertEqual(self.queued("claude_review_lang"), [])

    def test_fact_outside_beat_red(self):
        self.approve_source()
        self.rewrite(en_doc(b02=[{"id": "s003", "text": "Tran Hung Dao's men captured Omar at the Bach Dang River.",
                                  "facts": ["F002", "F001"], "kind": "fact", "note": ""}]))
        saved = self.script.load(self.pdir, "en")
        self.assertEqual(saved["lang"], "en")
        self.assertTrue(all(s["reviewed"] is False for _, s in self.script.sentences(saved)))
        self.assertFalse(os.path.exists(os.path.join(self.pdir, "script", "versions")))  # vi script untouched
        check = self.ls.check(self.pdir, "en")
        self.assertEqual(self.row(check, "s003")["colour"], "red")
        self.assertIn("dữ kiện không thuộc cảnh này", " ".join(self.row(check, "s003")["reasons"]))
        self.assertIn("dữ kiện không thuộc cảnh này", " ".join(check["per_sentence"]["s003"]))
        self.assertTrue(os.path.isfile(os.path.join(self.pdir, "lang", "en", "script", "check.json")))
        self.assertEqual(len(self.queued("claude_review_lang")), 1)
        with self.assertRaises(ValueError):
            self.script.approve(self.pdir, "owner", lang="en")

    def test_number_not_in_facts_red(self):
        self.approve_source()
        self.rewrite(en_doc(b01=[{"id": "s001", "text": "In 1287, the Yuan fleet came back.", "facts": ["F001"], "kind": "fact", "note": ""}]))
        r = self.row(self.ls.check(self.pdir, "en"), "s001")
        self.assertEqual(r["colour"], "red")
        self.assertIn("1287", " ".join(r["reasons"]))

    def test_glossary_miss_yellow(self):
        self.approve_source()
        doc = en_doc(b02=[{"id": "s003", "text": "The prince's men captured Omar.", "facts": ["F002"], "kind": "fact", "note": ""}])
        for _, s in self.script.sentences(doc):
            s["reviewed"] = True
        self.script.save(self.pdir, doc, "claude", lang="en")
        check = self.ls.check(self.pdir, "en")
        self.assertEqual(check["glossary_misses"], 1)
        self.assertEqual(self.row(check, "s003")["colour"], "yellow")
        self.assertIn("Tran Hung Dao", " ".join(self.row(check, "s003")["reasons"]))
        self.assertEqual(self.row(check, "s002")["colour"], "green")
        self.assertEqual(check["problems"], [])

    def review(self, result):
        self.approve_source()
        self.script.save(self.pdir, en_doc(), "agy", lang="en")
        self.fixture({"result.json": result})
        j = self.jobs.enqueue("claude_review_lang", {"project": "001-a", "lang": "en"}, "001-a", "Claude soát EN")
        self.assertEqual(j["argv"][0], self.w.CLAUDE)
        self.assertNotIn("--add-dir", j["argv"])
        self.assertNotIn("--dangerously-skip-permissions", j["argv"])
        for name in ("script.json", "outline.json", "glossary.json", "style.md", "check.json", "REVIEW_LANG.md"):
            self.assertTrue(os.path.isfile(os.path.join(j["params"]["run"], name)), name)
        self.assertEqual(self.run_job(j), "done")

    def test_review_clean_auto_approves(self):
        self.review(dict(en_doc(), flags=[]))
        saved = self.script.load(self.pdir, "en")
        self.assertTrue(saved["approved"])
        self.assertEqual(saved["approved_by"], "auto")
        self.assertTrue(all(s["reviewed"] for _, s in self.script.sentences(saved)))
        st = [l for l in self.progress.get(self.pdir)["langs"] if l["code"] == "en"][0]
        self.assertEqual(st["parts"]["script"], "done")
        self.assertEqual([i for i in self.inbox.open_items() if i["kind"] == "lang_flag"], [])

    def test_review_flags_go_to_inbox_with_back_translation(self):
        self.review(dict(en_doc(), flags=[{"sentence": "s003", "issue": "giọng hơi nặng",
                                           "back_translation_vi": "Quân của Trần Hưng Đạo bắt được Ô Mã Nhi."}]))
        saved = self.script.load(self.pdir, "en")
        self.assertFalse(saved["approved"])
        self.assertEqual(saved["flags"][0]["sentence"], "s003")
        items = [i for i in self.inbox.open_items() if i["kind"] == "lang_flag"]
        self.assertEqual([i["text"] for i in items],
                         ["EN câu s003: giọng hơi nặng — dịch lại: Quân của Trần Hưng Đạo bắt được Ô Mã Nhi."])
        self.assertEqual(items[0]["screen"], "langs")
        st = [l for l in self.progress.get(self.pdir)["langs"] if l["code"] == "en"][0]
        self.assertEqual(st["parts"]["script"], "wait")
        self.script.approve(self.pdir, "owner", lang="en")  # the owner decides: approval clears the flags
        self.assertEqual([i for i in self.inbox.open_items() if i["kind"] == "lang_flag"], [])

    def test_vi_paths_unchanged(self):
        self.script.save(self.pdir, json.loads(json.dumps(SRC)), "owner")
        self.assertTrue(os.path.isfile(os.path.join(self.pdir, "script", "script.json")))
        self.assertEqual(self.script.load(self.pdir, "vi"), self.script.load(self.pdir))
        self.assertEqual(self.script.report(self.pdir, "vi"), self.script.report(self.pdir))
        self.script.save(self.pdir, en_doc(), "agy", lang="en")
        self.assertTrue(os.path.isfile(os.path.join(self.pdir, "lang", "en", "script", "script.json")))
        self.assertEqual(self.script.load(self.pdir)["version"], 1)
        self.assertEqual(self.script.load(self.pdir)["lang"], "vi")
        self.assertEqual(self.script.load(self.pdir, "en")["lang"], "en")
        steps = {s["id"]: s["state"] for s in self.progress.get(self.pdir)["steps"]}
        self.assertEqual(steps["script"], "doing")
        st = [l for l in self.progress.get(self.pdir)["langs"] if l["code"] == "en"][0]
        self.assertEqual(st["parts"]["script"], "doing")

    def test_rejected_fact_unapproves_language(self):
        self.review(dict(en_doc(), flags=[]))
        self.assertTrue(self.script.load(self.pdir, "en")["approved"])
        self.fixture({"result.json": [{"id": "F002", "status": "rejected", "note": "sai"}]})
        j = self.jobs.enqueue("claude_verify", {"project": "001-a", "facts": ["F002"]}, "001-a", "v")
        self.run_job(j)
        self.assertFalse(self.script.load(self.pdir, "en")["approved"])


if __name__ == "__main__":
    unittest.main()
