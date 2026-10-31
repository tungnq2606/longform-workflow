import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

from tools.longform import inbox, jobs


def py(code):
    return lambda params: [sys.executable, "-c", code]


class JobsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.environ["LONGFORM_ROOT"] = self.root
        self.p = mock.patch.object(inbox.notify, "send", lambda t: True)
        self.p.start()
        self.kinds = dict(jobs.KINDS)
        jobs.register(jobs.Kind("hi", "x", py("print('hi')")))
        jobs.register(jobs.Kind("sleep", "x", py("import time; time.sleep(0.6)")))
        jobs.register(jobs.Kind("sleep_y", "y", py("import time; time.sleep(0.6)")))
        jobs.register(jobs.Kind("fail", "x", py("import sys; sys.exit(3)")))
        jobs.register(jobs.Kind("missing", "x", lambda p: ["/nonexistent/x"]))

        def strict(params):
            if "n" not in params:
                raise ValueError("thiếu n")
            return [sys.executable, "-c", "print(%d)" % params["n"]]
        jobs.register(jobs.Kind("strict", "x", strict))
        jobs.register(jobs.Kind("comments", "x", py("print('# skip'); print('keep')"),
                                on_line=lambda job, line: None if line.startswith("#") else line))
        self.runner = jobs.Runner({"x": 3, "y": 1})

    def tearDown(self):
        self.runner.stop()
        self.p.stop()
        jobs.KINDS.clear()
        jobs.KINDS.update(self.kinds)
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def wait(self, job_id, *states, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            self.runner.tick()
            st = jobs.get(job_id)["status"]
            if st in states:
                return st
            time.sleep(0.05)
        self.fail("job %s stuck in %s" % (job_id, jobs.get(job_id)["status"]))

    def test_enqueue_validates(self):
        with self.assertRaises(ValueError):
            jobs.enqueue("strict", {}, None, "s")
        with self.assertRaises(ValueError):
            jobs.enqueue("nope", {}, None, "s")
        self.assertEqual(jobs.list_jobs(), [])

    def test_runs_and_logs(self):
        j = jobs.enqueue("hi", {}, "001-a", "chào")
        self.assertEqual(j["status"], "queued")
        self.assertEqual(self.wait(j["id"], "done"), "done")
        text, off = jobs.read_log(j["id"])
        self.assertEqual(text, "hi\n")
        self.assertEqual(jobs.read_log(j["id"], off), ("", off))

    def test_lane_limit(self):
        r = jobs.Runner({"x": 1})
        a = jobs.enqueue("sleep", {}, None, "a")
        b = jobs.enqueue("sleep", {}, None, "b")
        r.tick()
        self.assertEqual([jobs.get(a["id"])["status"], jobs.get(b["id"])["status"]], ["running", "queued"])
        self.runner = r
        self.wait(b["id"], "done")

    def test_lanes_independent(self):
        r = jobs.Runner({"x": 1, "y": 1})
        a = jobs.enqueue("sleep", {}, None, "a")
        b = jobs.enqueue("sleep_y", {}, None, "b")
        r.tick()
        self.assertEqual([jobs.get(a["id"])["status"], jobs.get(b["id"])["status"]], ["running", "running"])
        self.runner = r
        self.wait(a["id"], "done")
        self.wait(b["id"], "done")

    def test_pause_lets_running_finish(self):
        ids = [jobs.enqueue("sleep", {}, None, str(i))["id"] for i in range(4)]
        self.runner.tick()
        jobs.set_paused(True, "test")
        self.assertTrue(jobs.paused()["on"])
        for i in ids[:3]:
            self.assertEqual(self.wait(i, "done"), "done")
        for _ in range(5):
            self.runner.tick()
        self.assertEqual(jobs.get(ids[3])["status"], "queued")
        jobs.set_paused(False)
        self.runner.tick()
        self.assertIn(jobs.get(ids[3])["status"], ("running", "done"))
        self.wait(ids[3], "done")

    def test_failure_goes_to_inbox(self):
        j = jobs.enqueue("fail", {}, "001-a", "hỏng thử")
        self.wait(j["id"], "failed")
        self.assertEqual(jobs.get(j["id"])["exit"], 3)
        items = inbox.open_items()
        self.assertEqual([i["kind"] for i in items], ["job_failed"])
        self.assertEqual(items[0]["project"], "001-a")

    def test_missing_binary_fails_cleanly(self):
        j = jobs.enqueue("missing", {}, None, "thiếu lệnh")
        self.wait(j["id"], "failed")
        self.assertIn("không tìm thấy lệnh", jobs.get(j["id"])["error"])
        self.assertEqual(len(inbox.open_items()), 1)

    def test_stop_running(self):
        j = jobs.enqueue("sleep", {}, None, "s")
        self.runner.tick()
        self.assertTrue(jobs.stop(j["id"]))
        self.assertEqual(self.wait(j["id"], "stopped"), "stopped")
        self.assertEqual(inbox.open_items(), [])

    def test_stop_queued(self):
        jobs.set_paused(True)
        j = jobs.enqueue("hi", {}, None, "s")
        self.assertTrue(jobs.stop(j["id"]))
        self.assertEqual(jobs.get(j["id"])["status"], "stopped")

    def test_recover_interrupted(self):
        j = jobs.enqueue("hi", {}, "001-a", "đang chạy dở")
        jobs._write(dict(jobs.get(j["id"]), status="running", pid=999999))
        self.assertEqual(jobs.recover(), 1)
        self.assertEqual(jobs.get(j["id"])["status"], "interrupted")
        self.assertEqual([i["kind"] for i in inbox.open_items()], ["job_interrupted"])

    def test_recover_calls_on_end(self):
        ended = []
        jobs.register(jobs.Kind("ends", "x", py("print(1)"), on_end=lambda job: ended.append((job["id"], job["status"]))))
        jobs.register(jobs.Kind("ends_boom", "x", py("print(1)"), on_end=mock.Mock(side_effect=RuntimeError("boom"))))
        j = jobs.enqueue("ends", {}, "001-a", "đang chạy dở")
        b = jobs.enqueue("ends_boom", {}, "001-a", "đang chạy dở 2")
        for x in (j, b):
            jobs._write(dict(jobs.get(x["id"]), status="running", pid=999999))
        self.assertEqual(jobs.recover(), 2)  # a broken on_end does not stop recover
        self.assertEqual(ended, [(j["id"], "interrupted")])
        self.assertIn("on_end lỗi", jobs.read_log(b["id"])[0])

    def test_stop_queued_calls_on_end(self):
        ended = []
        jobs.register(jobs.Kind("ends", "x", py("print(1)"), on_end=lambda job: ended.append(job["status"])))
        jobs.set_paused(True)
        j = jobs.enqueue("ends", {}, None, "s")
        self.assertTrue(jobs.stop(j["id"]))
        self.assertEqual(ended, ["stopped"])

    def test_on_line_filters(self):
        j = jobs.enqueue("comments", {}, None, "c")
        self.wait(j["id"], "done")
        self.assertEqual(jobs.read_log(j["id"])[0], "keep\n")

    def test_crash_in_run_frees_lane(self):
        def boom(job, line):
            raise RuntimeError("on_line hỏng")
        jobs.register(jobs.Kind("boom", "x", py("print('x')"), on_line=boom))
        jobs.register(jobs.Kind("nul", "x", lambda p: [sys.executable, "-c", "print(1)\x00"]))
        r = jobs.Runner({"x": 1})
        self.runner = r
        a = jobs.enqueue("boom", {}, None, "a")
        self.assertEqual(self.wait(a["id"], "failed", "done"), "failed")
        b = jobs.enqueue("nul", {}, None, "b")
        self.assertEqual(self.wait(b["id"], "failed", "done"), "failed")
        c = jobs.enqueue("hi", {}, None, "c")
        self.assertEqual(self.wait(c["id"], "done"), "done")  # lane not blocked

    def test_stop_kills_child_processes(self):
        code = "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); time.sleep(30)"
        jobs.register(jobs.Kind("tree", "x", py(code)))
        j = jobs.enqueue("tree", {}, None, "tree")
        self.runner.tick()
        time.sleep(0.5)
        jobs.stop(j["id"])
        self.assertEqual(self.wait(j["id"], "stopped", timeout=8), "stopped")

    def test_crash_in_run_frees_lane(self):
        def boom(job, line):
            raise RuntimeError("on_line hỏng")
        jobs.register(jobs.Kind("boom", "x", py("print('x')"), on_line=boom))
        jobs.register(jobs.Kind("nul", "x", lambda p: [sys.executable, "-c", "print(1)\x00"]))
        r = jobs.Runner({"x": 1})
        self.runner = r
        a = jobs.enqueue("boom", {}, None, "a")
        self.assertEqual(self.wait(a["id"], "failed", "done"), "failed")
        b = jobs.enqueue("nul", {}, None, "b")
        self.assertEqual(self.wait(b["id"], "failed", "done"), "failed")
        c = jobs.enqueue("hi", {}, None, "c")
        self.assertEqual(self.wait(c["id"], "done"), "done")  # lane not blocked

    def test_stop_kills_child_processes(self):
        code = "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); time.sleep(30)"
        jobs.register(jobs.Kind("tree", "x", py(code)))
        j = jobs.enqueue("tree", {}, None, "tree")
        self.runner.tick()
        time.sleep(0.5)
        jobs.stop(j["id"])
        self.assertEqual(self.wait(j["id"], "stopped", timeout=8), "stopped")

    def test_cwd_from_job(self):
        def build(params):
            os.makedirs(os.path.join(self.root, "run1"))
            params["run"] = os.path.join(self.root, "run1")  # build may add derived keys to params
            return [sys.executable, "-c", "open('here.txt', 'w').write('x')"]
        jobs.register(jobs.Kind("incwd", "x", build, cwd=lambda job: job["params"]["run"]))
        j = jobs.enqueue("incwd", {}, None, "cwd")
        self.assertEqual(j["params"]["run"], os.path.join(self.root, "run1"))
        self.wait(j["id"], "done")
        self.assertTrue(os.path.isfile(os.path.join(self.root, "run1", "here.txt")))

    def test_list_order(self):
        jobs.set_paused(True)
        a = jobs.enqueue("hi", {}, None, "a")
        b = jobs.enqueue("hi", {}, None, "b")
        self.assertEqual([j["id"] for j in jobs.list_jobs()], [a["id"], b["id"]])


if __name__ == "__main__":
    unittest.main()
