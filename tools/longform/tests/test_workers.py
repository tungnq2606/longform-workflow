"""AI workers with fake agy/claude binaries: each fake copies the fixture folder named in $FAKE_SRC into its cwd."""
import json
import os
import shutil
import stat
import sys
import tempfile
import time
import unittest
from unittest import mock

WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FAKE = """#!%s
import json, os, shutil, sys
src = os.environ.get("FAKE_SRC", "")
if src:
    for name in os.listdir(src):
        p = os.path.join(src, name)
        if os.path.isdir(p):
            shutil.copytree(p, os.path.join(os.getcwd(), name), dirs_exist_ok=True)
        else:
            shutil.copy(p, os.path.join(os.getcwd(), name))
print(json.dumps({"status": "SUCCESS", "denied_actions": json.loads(os.environ.get("FAKE_DENIED", "[]"))}))
""" % sys.executable

PAGE = "https://example.org/a\nNăm Mậu Tý, quân Nguyên đến sông Bạch Đằng. Quân ta bắt được Ô Mã Nhi."


def claim(i, quote, **kw):
    c = {"id": i, "claim_vi": "claim " + i, "quote": quote, "url": "https://example.org/a", "page_file": "pages/001.txt",
         "grade": "A", "kind": "primary_record", "source_title": "Toàn thư", "conflicts_with": []}
    c.update(kw)
    return c


def script_doc(facts=("F001",)):
    return {"lang": "vi", "chapters": [{"id": "C01", "title": "Mở đầu", "beats": [{"id": "B01", "goal": "hook", "sentences": [
        {"id": "s001", "text": "Bạn có biết không?", "facts": [], "kind": "question", "note": ""},
        {"id": "s002", "text": "Rồi quân Nguyên đến sông Bạch Đằng.", "facts": list(facts), "kind": "fact", "note": ""}]}]}]}


class Base(unittest.TestCase):
    """Temp root, fake agy/claude, runner and helpers; no tests of its own (test_chat reuses it)."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "config"))
        for f in ("languages.json", "studio.json"):
            shutil.copy(os.path.join(WS, "config", f), os.path.join(self.root, "config"))
        os.makedirs(os.path.join(self.root, "library", "stylebook"))
        shutil.copy(os.path.join(WS, "library", "stylebook", "vi.json"), os.path.join(self.root, "library", "stylebook"))
        os.environ["LONGFORM_ROOT"] = self.root
        from tools.longform import agy, factbank, inbox, jobs, project, script, workers
        self.agy, self.fb, self.inbox, self.jobs, self.script, self.w = agy, factbank, inbox, jobs, script, workers
        self.patches = [mock.patch.object(inbox.notify, "send", lambda t: True)]
        fakes = []
        for name in ("fake_agy.py", "fake_claude.py"):  # two files, so a test can tell which binary a job runs
            fake = os.path.join(self.root, name)
            open(fake, "w").write(FAKE)
            os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)
            fakes.append(fake)
        self.patches += [mock.patch.object(agy, "AGY", fakes[0]), mock.patch.object(workers, "CLAUDE", fakes[1])]
        for p in self.patches:
            p.start()
        self.pdir = project.create_project(1, "a", "A", [])
        self.runner = jobs.Runner({"agy": 1, "claude": 1})
        self.fix = os.path.join(self.root, "fixture")

    def tearDown(self):
        for p in self.patches:
            p.stop()
        for k in ("LONGFORM_ROOT", "FAKE_SRC", "FAKE_DENIED"):
            os.environ.pop(k, None)
        shutil.rmtree(self.root)

    def fixture(self, files):
        shutil.rmtree(self.fix, ignore_errors=True)
        os.makedirs(os.path.join(self.fix, "pages"))
        for name, text in files.items():
            with open(os.path.join(self.fix, name), "w", encoding="utf-8") as f:
                f.write(text if isinstance(text, str) else json.dumps(text, ensure_ascii=False))
        os.environ["FAKE_SRC"] = self.fix

    def run_job(self, job):
        """Start this job only (follow-up jobs it queues stay queued), wait for it and its on_end."""
        end = time.time() + 15
        while self.jobs.get(job["id"])["status"] == "queued" and time.time() < end:
            self.runner.tick()
            time.sleep(0.05)
        while time.time() < end:
            st = self.jobs.get(job["id"])["status"]
            if st not in ("queued", "running"):
                time.sleep(0.2)  # on_end runs right after the status is written
                return st
            time.sleep(0.05)
        self.fail("job stuck")

    def seed_bank(self, *claims):
        self.fixture({"sources.jsonl": "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in claims), "pages/001.txt": PAGE})
        self.fb.import_research(self.pdir, self.fix, "seed")

    def queued(self, kind):
        return [j for j in self.jobs.list_jobs() if j["kind"] == kind and j["status"] == "queued"]


class WorkersTest(Base):
    def test_agy_argv_no_skip(self):
        argv = self.agy.argv("do it")
        self.assertEqual(argv[:3], [self.agy.AGY, "-p", "do it"])
        self.assertIn("--sandbox", argv)
        self.assertNotIn("--dangerously-skip-permissions", argv)

    def test_agy_denied_fails_job(self):
        self.fixture({})
        os.environ["FAKE_DENIED"] = json.dumps([{"action": "mcp", "display_name": "CallMcpTool"}])
        j = self.jobs.enqueue("agy_research", {"project": "001-a", "request": "x"}, "001-a", "r")
        self.run_job(j)
        items = self.inbox.open_items()
        self.assertTrue(any("agy bị chặn quyền" in i["text"] and "CallMcpTool" in i["text"] for i in items))

    def test_research_imports_and_queues_verify(self):
        self.fixture({"sources.jsonl": json.dumps(claim("S1", "quân Nguyên đến sông Bạch Đằng"), ensure_ascii=False) + "\n",
                      "pages/001.txt": PAGE})
        j = self.jobs.enqueue("agy_research", {"project": "001-a", "request": "Bạch Đằng 1288"}, "001-a", "r")
        self.assertTrue(os.path.isfile(os.path.join(j["params"]["run"], "TASK.md")))
        self.assertIn("Bạch Đằng 1288", open(os.path.join(j["params"]["run"], "TASK.md")).read())
        self.assertEqual(self.run_job(j), "done")
        _, facts = self.fb.load(self.pdir)
        self.assertEqual([f["status"] for f in facts.values()], ["pending"])
        v = self.queued("claude_verify")
        self.assertEqual([x["params"]["facts"] for x in v], [["F001"]])

    def test_verify_applies_statuses(self):
        self.seed_bank(claim("S1", "quân Nguyên đến sông Bạch Đằng"), claim("S2", "Quân ta bắt được Ô Mã Nhi"))
        self.fixture({"result.json": [{"id": "F001", "status": "verified", "grade": "A", "note": "khớp"},
                                      {"id": "F002", "status": "weak", "grade": "B", "note": "mơ hồ"}]})
        j = self.jobs.enqueue("claude_verify", {"project": "001-a", "facts": ["F001", "F002"]}, "001-a", "v")
        argv = j["argv"]
        self.assertEqual(argv[0], self.w.CLAUDE)
        self.assertNotIn("--dangerously-skip-permissions", argv)
        self.assertEqual(self.run_job(j), "done")
        _, facts = self.fb.load(self.pdir)
        self.assertEqual((facts["F001"]["status"], facts["F001"]["checked_by"]), ("verified", "claude"))
        self.assertEqual((facts["F002"]["status"], facts["F002"]["grade"]), ("weak", "B"))

    def test_verify_conflict_status(self):
        self.seed_bank(claim("S1", "quân Nguyên đến sông Bạch Đằng", conflicts_with=["S2"]),
                       claim("S2", "Quân ta bắt được Ô Mã Nhi", conflicts_with=["S1"]))
        self.fixture({"result.json": [{"id": "F001", "status": "verified", "grade": "A", "note": ""},
                                      {"id": "F002", "status": "rejected", "grade": "A", "note": ""}]})
        self.run_job(self.jobs.enqueue("claude_verify", {"project": "001-a", "facts": ["F001", "F002"]}, "001-a", "v"))
        _, facts = self.fb.load(self.pdir)
        self.assertEqual((facts["F001"]["status"], facts["F002"]["status"]), ("conflict", "rejected"))

    def test_draft_saves_and_queues_review(self):
        self.seed_bank(claim("S1", "quân Nguyên đến sông Bạch Đằng"))
        self.fb.set_status(self.pdir, "F001", "verified", "claude", "")
        self.fixture({"result.json": script_doc()})
        j = self.jobs.enqueue("agy_draft", {"project": "001-a", "request": "10 phút"}, "001-a", "d")
        run = j["params"]["run"]
        self.assertEqual([f["id"] for f in json.load(open(os.path.join(run, "facts.json")))], ["F001"])
        self.assertIn("chúng ta", open(os.path.join(run, "style.md")).read())
        self.assertEqual(self.run_job(j), "done")
        self.assertEqual((self.script.load(self.pdir)["version"], self.script.load(self.pdir)["updated_by"]), (1, "agy"))
        self.assertEqual(len(self.queued("claude_review")), 1)

    def test_draft_unknown_fact_rejected(self):
        self.seed_bank(claim("S1", "quân Nguyên đến sông Bạch Đằng"))  # F001 stays pending: not usable
        self.fixture({"result.json": script_doc(["F001", "F777"])})
        self.run_job(self.jobs.enqueue("agy_draft", {"project": "001-a", "request": "x"}, "001-a", "d"))
        self.assertIsNone(self.script.load(self.pdir))
        self.assertTrue(any("không dùng được" in i["text"] for i in self.inbox.open_items()))
        self.assertEqual(self.queued("claude_review"), [])

    def test_review_sets_wait_and_inbox(self):
        self.seed_bank(claim("S1", "quân Nguyên đến sông Bạch Đằng"))
        self.fb.set_status(self.pdir, "F001", "verified", "claude", "")
        self.script.save(self.pdir, script_doc(), "agy")
        revised = script_doc()
        revised["notes"] = [{"sentence": "s002", "note": "gọn hơn"}]
        self.fixture({"result.json": revised})
        self.assertEqual(self.run_job(self.jobs.enqueue("claude_review", {"project": "001-a"}, "001-a", "rv")), "done")
        d = self.script.load(self.pdir)
        self.assertEqual((d["version"], d["updated_by"], d["review_notes"]), (2, "claude", [{"sentence": "s002", "note": "gọn hơn"}]))
        from tools.longform import progress
        self.assertEqual(progress.get(self.pdir)["steps"][1]["state"], "wait")
        items = [i for i in self.inbox.open_items() if i["kind"] == "script_approve"]
        self.assertEqual(len(items), 1)
        self.assertIn("v2", items[0]["text"])

    def test_import_bad_result_keeps_bank(self):
        self.seed_bank(claim("S1", "quân Nguyên đến sông Bạch Đằng"))
        self.fixture({"result.json": "{not json"})
        self.run_job(self.jobs.enqueue("claude_verify", {"project": "001-a", "facts": ["F001"]}, "001-a", "v"))
        self.assertEqual(self.fb.load(self.pdir)[1]["F001"]["status"], "pending")
        self.fixture({"result.json": [{"id": "F999", "status": "verified", "grade": "A", "note": ""}]})
        self.run_job(self.jobs.enqueue("claude_verify", {"project": "001-a", "facts": ["F001"]}, "001-a", "v"))
        self.assertEqual(self.fb.load(self.pdir)[1]["F001"]["status"], "pending")
        self.assertEqual(len([i for i in self.inbox.open_items() if "không dùng được" in i["text"]]), 2)

    def test_build_rejects_bad_project(self):
        with self.assertRaises(ValueError):
            self.jobs.enqueue("agy_research", {"project": "../x", "request": "x"}, None, "r")
        with self.assertRaises(ValueError):
            self.jobs.enqueue("claude_verify", {"project": "001-a", "facts": ["F404"]}, "001-a", "v")


if __name__ == "__main__":
    unittest.main()
