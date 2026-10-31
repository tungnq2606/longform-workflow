import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from tools.longform.tests import test_workers as tw


class ChatTest(tw.Base):
    def setUp(self):
        super().setUp()
        from tools.longform import chat
        self.chat = chat
        self.seed_bank(tw.claim("S1", "quân Nguyên đến sông Bạch Đằng"), tw.claim("S2", "Quân ta bắt được Ô Mã Nhi"))
        self.fb.set_status(self.pdir, "F001", "verified", "claude", "")
        self.fb.set_status(self.pdir, "F002", "rejected", "claude", "")
        self.script.save(self.pdir, tw.script_doc(), "agy")

    def send(self, result, message="viết lại câu s002"):
        self.fixture({"result.json": result})
        j = self.jobs.enqueue("agy_chat", {"project": "001-a", "message": message}, "001-a", "chat")
        self.run_job(j)
        return j

    def test_build_writes_context_no_claude(self):
        self.fixture({})
        j = self.jobs.enqueue("agy_chat", {"project": "001-a", "message": "chào"}, "001-a", "chat")
        self.assertEqual(j["argv"][0], self.agy.AGY)
        self.assertFalse(any("claude" in a.lower() for a in j["argv"][:1]))
        self.assertNotIn(self.w.CLAUDE, j["argv"])
        run = j["params"]["run"]
        for name in ("CHAT.md", "script.json", "report.json", "facts.json", "style.md", "chat_history.md"):
            self.assertTrue(os.path.isfile(os.path.join(run, name)), name)
        self.assertIn("chào", open(os.path.join(run, "CHAT.md")).read())
        self.assertEqual(self.chat.history(self.pdir)[-1]["role"], "owner")

    def test_edits_applied(self):
        self.send({"reply": "Đã sửa.", "edits": [
            {"op": "set", "id": "s002", "text": "Rồi quân Nguyên kéo đến sông Bạch Đằng.", "facts": ["F001"]},
            {"op": "add", "beat": "B01", "after": "s001", "text": "Nghe hấp dẫn chưa?", "facts": []},
            {"op": "delete", "id": "s001"}]})
        d = self.script.load(self.pdir)
        ss = d["chapters"][0]["beats"][0]["sentences"]
        self.assertEqual([s["id"] for s in ss], ["s003", "s002"])
        self.assertEqual(ss[1]["text"], "Rồi quân Nguyên kéo đến sông Bạch Đằng.")
        self.assertEqual((d["version"], d["updated_by"]), (2, "agy-chat"))
        h = self.chat.history(self.pdir)
        self.assertEqual([(m["role"], m["text"]) for m in h[-3:]],
                         [("owner", "viết lại câu s002"), ("agy", "Đã sửa."), ("system", "Đã lưu kịch bản v2.")])

    def test_chat_edits_marked_unreviewed(self):
        self.send({"reply": "Ok.", "edits": [
            {"op": "set", "id": "s002", "text": "Rồi quân Nguyên kéo đến sông Bạch Đằng.", "facts": ["F001"]}]})
        ss = {x["id"]: x for _, x in self.script.sentences(self.script.load(self.pdir))}
        self.assertIs(ss["s002"]["reviewed"], False)

    def test_bad_shapes_refused_with_message(self):
        self.send({"reply": "Ok.", "edits": [{"op": "set", "id": ["s002"], "text": "x", "facts": [["F001"]]}]})
        self.assertEqual(self.script.load(self.pdir)["version"], 1)
        self.assertEqual(self.chat.history(self.pdir)[-1]["role"], "system")

    def test_stale_chat_edit_refused(self):
        self.fixture({"result.json": {"reply": "Ok.", "edits": [{"op": "delete", "id": "s001"}]}})
        j = self.jobs.enqueue("agy_chat", {"project": "001-a", "message": "bỏ câu 1"}, "001-a", "chat")
        self.script.save(self.pdir, self.script.load(self.pdir), "owner")  # v2 while agy works on v1
        self.run_job(j)
        self.assertEqual(self.script.load(self.pdir)["version"], 2)
        self.assertIn("đã đổi", self.chat.history(self.pdir)[-1]["text"])

    def test_edit_with_rejected_fact_refused_whole(self):
        self.send({"reply": "Đã sửa.", "edits": [
            {"op": "set", "id": "s001", "text": "Bạn đoán thử?", "facts": []},
            {"op": "set", "id": "s002", "text": "Ô Mã Nhi bị bắt.", "facts": ["F002"]}]})
        self.assertEqual(self.script.load(self.pdir)["version"], 1)
        last = self.chat.history(self.pdir)[-1]
        self.assertEqual(last["role"], "system")
        self.assertIn("F002", last["text"])

    def test_research_request_enqueues_agy_research(self):
        self.send({"reply": "Ngân hàng chưa có, tôi đi tìm.", "edits": [], "research": "số thuyền Nguyên năm 1288"})
        q = self.queued("agy_research")
        self.assertEqual([x["params"]["request"] for x in q], ["số thuyền Nguyên năm 1288"])
        self.assertEqual(q[0]["argv"][0], self.agy.AGY)

    def test_draft_request_enqueues_agy_draft(self):
        self.send({"reply": "Viết lại cả bài.", "edits": [], "draft": "giọng vui hơn"})
        self.assertEqual(len(self.queued("agy_draft")), 1)

    def test_rule_proposed(self):
        from tools.longform import stylebook
        self.send({"reply": "Ok.", "edits": [], "rule": "Không dùng từ 'siêu'"}, message="đừng dùng chữ siêu")
        self.assertTrue(any(r["text"] == "Không dùng từ 'siêu'" and r["status"] == "proposed" for r in stylebook.load("vi")["rules"]))

    def test_bad_result_keeps_script(self):
        self.send("{oops")
        self.assertEqual(self.script.load(self.pdir)["version"], 1)
        self.assertEqual(self.chat.history(self.pdir)[-1]["role"], "system")

    def test_rejects_empty_message(self):
        with self.assertRaises(ValueError):
            self.jobs.enqueue("agy_chat", {"project": "001-a", "message": " "}, "001-a", "chat")


if __name__ == "__main__":
    unittest.main()
