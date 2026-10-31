import json
import os
import shutil
import tempfile
import unittest

WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class ClaudeBoxTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "config"))
        for f in ("languages.json", "studio.json"):
            shutil.copy(os.path.join(WS, "config", f), os.path.join(self.root, "config"))
        os.environ["LONGFORM_ROOT"] = self.root
        from tools.longform import claude_box, project
        self.cb = claude_box
        project.create_project(1, "a", "A", [])

    def tearDown(self):
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def test_registers_kind(self):
        from tools.longform import jobs
        self.assertEqual(jobs.KINDS["claude"].lane, "claude")

    def test_build_new_session(self):
        argv = self.cb.build({"message": "chào", "project": "001-a"})
        self.assertEqual(argv[:3], ["claude", "-p", "chào"])
        sid = argv[argv.index("--session-id") + 1]
        with open(os.path.join(self.cb.session_dir("001-a"), "session")) as f:
            self.assertEqual(f.read().strip(), sid)
        self.assertIn("projects/001-a", argv[argv.index("--append-system-prompt") + 1])

    def test_build_resumes(self):
        a = self.cb.build({"message": "1", "project": "001-a"})
        b = self.cb.build({"message": "2", "project": "001-a"})
        self.assertNotIn("--resume", a)
        self.assertEqual(b[b.index("--resume") + 1], a[a.index("--session-id") + 1])

    def test_general_session(self):
        argv = self.cb.build({"message": "x", "project": None})
        self.assertIn("--session-id", argv)
        self.assertTrue(self.cb.session_dir(None).endswith(os.path.join("studio", "state", "claude-general")))

    def test_no_skip_permissions(self):
        argv = self.cb.build({"message": "x", "project": "001-a"})
        self.assertNotIn("--dangerously-skip-permissions", argv)
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "acceptEdits")
        self.assertIn("Read", argv[argv.index("--allowedTools") + 1:])

    def test_model_whitelist(self):
        a = self.cb.build({"message": "x", "project": "001-a", "model": "opus"})
        self.assertEqual(a[a.index("--model") + 1], "opus")
        b = self.cb.build({"message": "x", "project": "001-a", "model": "x; rm -rf"})
        self.assertNotIn("--model", b)

    def test_rejects_bad_project(self):
        for bad in ("../etc", "001-zzz", "abc"):
            with self.assertRaises(ValueError):
                self.cb.build({"message": "x", "project": bad})

    def test_rejects_empty_message(self):
        for m in ("", "   ", "x" * 8001, None):
            with self.assertRaises(ValueError):
                self.cb.build({"message": m, "project": None})

    def test_message_never_parsed_as_flag(self):
        argv = self.cb.build({"message": "--dangerously-skip-permissions", "project": None})
        self.assertFalse(argv[2].startswith("-"))
        self.assertEqual(argv[2].strip(), "--dangerously-skip-permissions")

    def test_on_line_text_and_tool(self):
        job = {"id": "j1"}
        text = json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Xin chào"}]}})
        tool = json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash",
                                                                          "input": {"command": "ls projects"}}]}})
        res = json.dumps({"type": "result", "subtype": "success", "duration_ms": 4200})
        self.assertEqual(self.cb.on_line(job, text), "Xin chào")
        self.assertEqual(self.cb.on_line(job, tool), "  → Bash ls projects")
        self.assertEqual(self.cb.on_line(job, res), "[xong: success, 4 s]")
        self.assertIsNone(self.cb.on_line(job, json.dumps({"type": "system"})))
        self.assertEqual(self.cb.on_line(job, "plain error"), "plain error")

    def test_history_roundtrip(self):
        self.cb.build({"message": "Câu hỏi", "project": "001-a"})
        job = {"id": "j2", "params": {"project": "001-a"}}
        self.cb.on_line(job, json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Trả lời"}]}}))
        self.cb.on_end(job)
        h = self.cb.history("001-a")
        self.assertEqual([(e["role"], e["text"]) for e in h], [("owner", "Câu hỏi"), ("claude", "Trả lời")])

    def test_history_no_answer(self):
        self.cb.on_end({"id": "j3", "params": {"project": None}})
        self.assertEqual(self.cb.history(None)[-1]["text"], "(không có trả lời)")


if __name__ == "__main__":
    unittest.main()
