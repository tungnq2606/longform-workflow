import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from unittest import mock

WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "config"))
        for f in ("languages.json", "studio.json"):
            shutil.copy(os.path.join(WS, "config", f), os.path.join(self.root, "config"))
        os.environ["LONGFORM_ROOT"] = self.root
        from studio import server
        from tools.longform import inbox, jobs
        self.server_mod, self.inbox, self.jobs = server, inbox, jobs
        self.p = mock.patch.object(inbox.notify, "send", lambda t: True)
        self.p.start()
        self.kinds = dict(jobs.KINDS)
        jobs.register(jobs.Kind("claude", "claude", lambda params: [sys.executable, "-c", "print(1)"]))
        self.srv = server.make_server(0, None)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.p.stop()
        self.jobs.KINDS.clear()
        self.jobs.KINDS.update(self.kinds)
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def req(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        h = {"Host": "127.0.0.1:%d" % self.port}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        raw = r.read()
        c.close()
        try:
            return r.status, json.loads(raw)
        except ValueError:
            return r.status, raw

    def test_binds_localhost_only(self):
        self.assertEqual(self.srv.server_address[0], "127.0.0.1")

    def test_home_lists_projects_and_inbox(self):
        from tools.longform import project
        project.create_project(1, "a", "A", ["en"])
        self.inbox.add("001-a", "test", "việc chờ")
        st, home = self.req("GET", "/api/home")
        self.assertEqual(st, 200)
        self.assertEqual([p["id"] for p in home["projects"]], ["001-a"])
        self.assertEqual(home["projects"][0]["total"], 7)
        self.assertEqual(home["projects"][0]["steps"], ["todo"] * 7)
        self.assertEqual([i["text"] for i in home["inbox"]], ["việc chờ"])
        self.assertFalse(home["paused"]["on"])

    def test_languages(self):
        st, langs = self.req("GET", "/api/languages")
        self.assertEqual([l["code"] for l in langs], ["vi", "en", "ja", "de", "es"])

    def test_create_project_then_get(self):
        st, out = self.req("POST", "/api/projects", {"title": "Bạch Đằng", "languages": ["en"]})
        self.assertEqual((st, out["id"]), (200, "001-bach-dang"))
        st, p = self.req("GET", "/api/projects/001-bach-dang")
        self.assertEqual(p["project"]["languages"], ["vi", "en"])
        self.assertEqual(len(p["progress"]["steps"]), 7)

    def test_create_project_bad_language(self):
        st, out = self.req("POST", "/api/projects", {"title": "X", "languages": ["fr"]})
        self.assertEqual(st, 400)
        self.assertIn("error", out)

    def test_rejects_foreign_origin(self):
        st, _ = self.req("POST", "/api/claude", {"message": "x"}, {"Origin": "https://evil.example"})
        self.assertEqual(st, 403)
        self.assertEqual(self.jobs.list_jobs(), [])

    def test_accepts_own_origin(self):
        st, _ = self.req("POST", "/api/claude", {"message": "x"}, {"Origin": "http://127.0.0.1:%d" % self.port})
        self.assertEqual(st, 200)

    def test_rejects_foreign_host(self):
        st, _ = self.req("GET", "/api/home", headers={"Host": "evil.example:%d" % self.port})
        self.assertEqual(st, 403)

    def test_rejects_non_json_post(self):
        st, _ = self.req("POST", "/api/pause", headers={"Content-Type": "text/plain"})
        self.assertEqual(st, 403)
        self.assertFalse(self.jobs.paused()["on"])

    def test_bad_project_id_404(self):
        self.assertEqual(self.req("GET", "/api/projects/..%2F..%2Fetc")[0], 404)
        self.assertEqual(self.req("GET", "/api/projects/009-none")[0], 404)

    def test_static_traversal_404(self):
        self.assertEqual(self.req("GET", "/static/../server.py")[0], 404)
        self.assertEqual(self.req("GET", "/static/%2e%2e/server.py")[0], 404)

    def test_index_served(self):
        st, body = self.req("GET", "/")
        self.assertEqual(st, 200)
        self.assertIn(b"<html", body.lower())

    def test_pause_endpoint(self):
        self.assertEqual(self.req("POST", "/api/pause", {"on": True})[0], 200)
        self.assertTrue(self.jobs.paused()["on"])
        self.req("POST", "/api/pause", {"on": False})
        self.assertFalse(self.jobs.paused()["on"])

    def test_claude_enqueues_job(self):
        from tools.longform import project
        project.create_project(1, "a", "A", [])
        st, job = self.req("POST", "/api/claude", {"message": "x", "project": "001-a"})
        self.assertEqual((st, job["status"], job["project"]), (200, "queued", "001-a"))
        st, lst = self.req("GET", "/api/jobs")
        self.assertEqual([j["id"] for j in lst], [job["id"]])
        st, log = self.req("GET", "/api/jobs/%s/log?offset=0" % job["id"])
        self.assertEqual(log, {"text": "", "offset": 0})
        self.assertEqual(self.req("POST", "/api/jobs/%s/stop" % job["id"], {})[1], {"ok": True})

    def test_inbox_done(self):
        it = self.inbox.add(None, "test", "x")
        self.assertEqual(self.req("POST", "/api/inbox/%s/done" % it["id"], {})[1], {"ok": True})
        self.assertEqual(self.inbox.open_items(), [])

    def test_home_has_library(self):
        st, home = self.req("GET", "/api/home")
        self.assertEqual(home["library"], {"characters": [], "backgrounds": [], "styles": []})

    def test_thumb(self):
        from PIL import Image
        os.makedirs(os.path.join(self.root, "library", "backgrounds"))
        Image.new("RGB", (1920, 1080), (1, 2, 3)).save(os.path.join(self.root, "library", "backgrounds", "b1.png"))
        st, body = self.req("GET", "/api/thumb/bg/b1")
        self.assertEqual(st, 200)
        self.assertEqual(body[:3], b"\xff\xd8\xff")  # JPEG
        self.assertEqual(self.req("GET", "/api/thumb/bg/nope")[0], 404)
        self.assertEqual(self.req("GET", "/api/thumb/bg/..%2Fb1")[0], 404)
        self.assertEqual(self.req("GET", "/api/thumb/zz/b1")[0], 404)

    def test_broken_project_json_skipped(self):
        from tools.longform import project
        project.create_project(1, "a", "A", [])
        os.makedirs(os.path.join(self.root, "projects", "002-bad"))
        open(os.path.join(self.root, "projects", "002-bad", "project.json"), "w").write("{broken")
        st, home = self.req("GET", "/api/home")
        self.assertEqual(st, 200)
        self.assertEqual([p["id"] for p in home["projects"]], ["001-a"])

    def test_unexpected_error_is_500_json(self):
        os.makedirs(os.path.join(self.root, "library", "backgrounds"))
        open(os.path.join(self.root, "library", "backgrounds", "bad.png"), "w").write("not a png")
        st, out = self.req("GET", "/api/thumb/bg/bad")
        self.assertEqual(st, 500)
        self.assertIn("error", out)

    def test_second_studio_does_not_touch_live_jobs(self):
        cfg = json.load(open(os.path.join(self.root, "config", "studio.json")))
        cfg["port"] = self.port  # the live test server holds this port
        json.dump(cfg, open(os.path.join(self.root, "config", "studio.json"), "w"))
        j = self.jobs.enqueue("claude", {}, None, "live")
        self.jobs._write(dict(self.jobs.get(j["id"]), status="running"))
        with self.assertRaises(OSError):
            self.server_mod.main()
        self.assertEqual(self.jobs.get(j["id"])["status"], "running")
        self.assertEqual(self.inbox.open_items(), [])

    def test_broken_project_json_skipped(self):
        from tools.longform import project
        project.create_project(1, "a", "A", [])
        os.makedirs(os.path.join(self.root, "projects", "002-bad"))
        open(os.path.join(self.root, "projects", "002-bad", "project.json"), "w").write("{broken")
        st, home = self.req("GET", "/api/home")
        self.assertEqual(st, 200)
        self.assertEqual([p["id"] for p in home["projects"]], ["001-a"])

    def test_unexpected_error_is_500_json(self):
        os.makedirs(os.path.join(self.root, "library", "backgrounds"))
        open(os.path.join(self.root, "library", "backgrounds", "bad.png"), "w").write("not a png")
        st, out = self.req("GET", "/api/thumb/bg/bad")
        self.assertEqual(st, 500)
        self.assertIn("error", out)

    def test_second_studio_does_not_touch_live_jobs(self):
        cfg = json.load(open(os.path.join(self.root, "config", "studio.json")))
        cfg["port"] = self.port  # the live test server holds this port
        json.dump(cfg, open(os.path.join(self.root, "config", "studio.json"), "w"))
        j = self.jobs.enqueue("claude", {}, None, "live")
        self.jobs._write(dict(self.jobs.get(j["id"]), status="running"))
        with self.assertRaises(OSError):
            self.server_mod.main()
        self.assertEqual(self.jobs.get(j["id"])["status"], "running")
        self.assertEqual(self.inbox.open_items(), [])

    def make_project_with_bank(self):
        from tools.longform import factbank, project
        project.create_project(1, "a", "A", [])
        pdir = os.path.join(self.root, "projects", "001-a")
        run = os.path.join(self.root, "run")
        os.makedirs(os.path.join(run, "pages"))
        open(os.path.join(run, "pages", "001.txt"), "w").write("https://x.org\nQuân Nguyên đến sông Bạch Đằng năm ấy.")
        c = {"id": "S1", "claim_vi": "Quân Nguyên đến Bạch Đằng", "quote": "Quân Nguyên đến sông Bạch Đằng", "url": "https://x.org",
             "page_file": "pages/001.txt", "grade": "A", "kind": "primary_record"}
        open(os.path.join(run, "sources.jsonl"), "w").write(json.dumps(c, ensure_ascii=False) + "\n")
        factbank.import_research(pdir, run, "seed")
        factbank.set_status(pdir, "F001", "verified", "claude", "")
        return pdir

    def test_facts_endpoint(self):
        self.make_project_with_bank()
        st, out = self.req("GET", "/api/projects/001-a/facts")
        self.assertEqual(st, 200)
        self.assertEqual(list(out["facts"]), ["F001"])
        self.assertEqual(out["sources"]["S001"]["url"], "https://x.org")

    def test_page_endpoint_only_bank_pages(self):
        self.make_project_with_bank()
        st, body = self.req("GET", "/api/projects/001-a/pages/001")
        self.assertEqual(st, 200)
        self.assertIn("Bạch Đằng".encode(), body)
        self.assertEqual(self.req("GET", "/api/projects/001-a/pages/002")[0], 404)
        self.assertEqual(self.req("GET", "/api/projects/001-a/pages/..%2F..%2Fproject")[0], 404)

    def test_script_endpoint_report(self):
        from tools.longform import script
        pdir = self.make_project_with_bank()
        st, out = self.req("GET", "/api/projects/001-a/script")
        self.assertEqual((st, out["script"]), (200, None))
        script.save(pdir, {"chapters": [{"id": "C01", "title": "", "beats": [{"id": "B01", "goal": "", "sentences": [
            {"id": "s001", "text": "Rồi Trần Hưng Đạo ra sông.", "facts": [], "kind": "fact", "note": ""}]}]}]}, "agy")
        st, out = self.req("GET", "/api/projects/001-a/script")
        self.assertEqual(out["report"]["red"], 1)
        st, out = self.req("POST", "/api/projects/001-a/script/sentence", {"id": "s001", "text": "Rồi Trần Hưng Đạo ra sông.", "facts": ["F001"]})
        self.assertEqual(st, 200)
        self.assertEqual(self.req("GET", "/api/projects/001-a/script")[1]["report"]["green"], 1)
        self.assertEqual(self.req("POST", "/api/projects/001-a/script/sentence", {"id": "s404", "text": "x", "facts": []})[0], 400)

    def test_approve_refused_with_red(self):
        from tools.longform import script
        pdir = self.make_project_with_bank()
        script.save(pdir, {"chapters": [{"id": "C01", "title": "", "beats": [{"id": "B01", "goal": "", "sentences": [
            {"id": "s001", "text": "Có 400 thuyền.", "facts": [], "kind": "fact", "note": ""}]}]}]}, "agy")
        st, out = self.req("POST", "/api/projects/001-a/script/approve", {})
        self.assertEqual(st, 400)
        self.assertIn("1 câu đỏ", out["error"])

    def test_ai_job_endpoints(self):
        from tools.longform import script
        pdir = self.make_project_with_bank()
        self.assertEqual(self.req("POST", "/api/projects/001-a/research", {"request": "Vân Đồn"})[1]["kind"], "agy_research")
        self.assertEqual(self.req("POST", "/api/projects/001-a/draft", {"request": "10 phút"})[1]["kind"], "agy_draft")
        self.assertEqual(self.req("POST", "/api/projects/001-a/review", {})[0], 400)  # no script yet
        st, job = self.req("POST", "/api/projects/001-a/chat", {"message": "chào"})
        self.assertEqual((st, job["kind"]), (200, "agy_chat"))
        self.assertEqual(self.req("GET", "/api/projects/001-a/chat")[1][-1]["text"], "chào")

    def test_fact_status_override(self):
        self.make_project_with_bank()
        st, f = self.req("POST", "/api/projects/001-a/facts/F001/status", {"status": "weak", "note": "nghi"})
        self.assertEqual((st, f["status"], f["checked_by"]), (200, "weak", "owner"))
        self.assertEqual(self.req("POST", "/api/projects/001-a/facts/F404/status", {"status": "weak"})[0], 404)
        self.assertEqual(self.req("POST", "/api/projects/001-a/facts/F001/status", {"status": "great"})[0], 400)

    def test_upload_type_and_size_checked(self):
        import base64
        self.make_project_with_bank()
        ok = {"name": "toan thu q5.pdf", "data": base64.b64encode(b"%PDF-1.4 x").decode()}
        st, job = self.req("POST", "/api/projects/001-a/sources/upload", ok)
        self.assertEqual((st, job["kind"]), (200, "agy_research"))
        saved = os.listdir(os.path.join(self.root, "projects", "001-a", "research", "uploads"))
        self.assertEqual(len(saved), 1)
        self.assertIn(saved[0], job["params"]["request"])
        self.assertEqual(self.req("POST", "/api/projects/001-a/sources/upload", {"name": "x.exe", "data": ok["data"]})[0], 400)
        self.assertEqual(self.req("POST", "/api/projects/001-a/sources/upload", {"name": "../../x.pdf", "data": ok["data"]})[0], 200)
        self.assertFalse(os.path.exists(os.path.join(self.root, "projects", "x.pdf")))
        from studio import server
        with mock.patch.object(server, "MAX_UPLOAD", 4):
            self.assertEqual(self.req("POST", "/api/projects/001-a/sources/upload", ok)[0], 400)

    def test_stylebook_decide(self):
        from tools.longform import stylebook
        r = stylebook.propose("vi", "Không dùng từ siêu", "test")
        st, book = self.req("GET", "/api/stylebook/vi")
        self.assertEqual(book["rules"][-1]["status"], "proposed")
        self.assertEqual(self.req("POST", "/api/stylebook/vi/%s/decide" % r["id"], {"keep": True})[1]["status"], "kept")
        self.assertEqual(self.req("POST", "/api/stylebook/vi/R99/decide", {"keep": True})[0], 404)
        self.assertEqual(self.req("GET", "/api/stylebook/xx")[0], 404)

    def test_claude_history(self):
        st, h = self.req("GET", "/api/claude/history")
        self.assertEqual((st, h), (200, []))
        self.assertEqual(self.req("GET", "/api/claude/history?project=..%2Fx")[0], 404)


if __name__ == "__main__":
    unittest.main()
