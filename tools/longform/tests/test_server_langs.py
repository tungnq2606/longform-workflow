"""Languages tab API (Plan 6): studio/routes_langs.py."""
import base64
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
MP3 = b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\x00" * 64
SRC = {"lang": "vi", "chapters": [{"id": "C01", "title": "Mở đầu", "beats": [{"id": "B01", "goal": "hook", "sentences": [
    {"id": "s001", "text": "Bạn có biết chuyện này không?", "facts": [], "kind": "question", "note": ""}]}]}]}


class ServerLangsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "config"))
        for f in ("languages.json", "studio.json"):
            shutil.copy(os.path.join(WS, "config", f), os.path.join(self.root, "config"))
        os.environ["LONGFORM_ROOT"] = self.root
        from studio import server
        from tools.longform import inbox, jobs, project, script
        self.server_mod, self.inbox, self.jobs, self.script = server, inbox, jobs, script
        self.p = mock.patch.object(inbox.notify, "send", lambda t: True)
        self.p.start()
        self.kinds = dict(jobs.KINDS)
        jobs.register(jobs.Kind("claude", "claude", lambda params: [sys.executable, "-c", "print(1)"]))
        jobs.register(jobs.Kind("timing_build", "cpu", lambda params: [sys.executable, "-c", "print(1)"]))  # Plan 5 owns it
        self.srv = server.make_server(0, None)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.pdir = project.create_project(1, "a", "A", ["en"])

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

    def approve_vi(self):
        self.script.save(self.pdir, json.loads(json.dumps(SRC)), "owner")
        self.script.approve(self.pdir, "owner")

    def test_lang_endpoint_shape(self):
        st, d = self.req("GET", "/api/projects/001-a/langs/en")
        self.assertEqual(st, 200)
        self.assertTrue({"script", "check", "voice", "timing", "upload", "render"} <= set(d))
        self.assertIsNone(d["script"])
        self.assertEqual(d["voice"]["parts"], [])
        self.assertFalse(d["timing"])
        st, d = self.req("GET", "/api/projects/001-a/langs/vi")
        self.assertEqual(st, 200)
        self.assertTrue(d["source"])
        self.assertEqual(self.req("GET", "/api/projects/001-a/langs/de")[0], 404)  # not a project language
        self.assertEqual(self.req("GET", "/api/projects/001-a/langs/xx")[0], 404)
        self.assertEqual(self.req("GET", "/api/projects/999-z/langs/en")[0], 404)
        st, out = self.req("POST", "/api/projects/001-a/langs/en/rewrite", {})
        self.assertEqual(st, 400)  # source script not approved yet
        self.assertIn("chưa chốt", out["error"])
        self.approve_vi()
        st, d = self.req("GET", "/api/projects/001-a/langs/en")
        self.assertEqual([b["beat"] for b in d["outline"]], ["B01"])

    def test_voice_drop_route(self):
        self.approve_vi()
        st, parts = self.req("POST", "/api/projects/001-a/langs/vi/voice/prepare", {})
        self.assertEqual((st, [p["part"] for p in parts]), (200, ["01"]))
        st, text = self.req("GET", "/api/projects/001-a/langs/vi/voice/parts/01.txt")
        self.assertEqual((st, text.decode()), (200, "Bạn có biết chuyện này không?"))
        self.assertEqual(self.req("GET", "/api/projects/001-a/langs/vi/voice/parts/02.txt")[0], 404)
        st, out = self.req("POST", "/api/projects/001-a/langs/vi/voice/drop", {"name": "02.mp3", "data": base64.b64encode(MP3).decode()})
        self.assertEqual(st, 400)
        st, out = self.req("POST", "/api/projects/001-a/langs/vi/voice/drop", {"name": "01.mp3", "data": "!!!"})
        self.assertEqual(st, 400)
        st, out = self.req("POST", "/api/projects/001-a/langs/vi/voice/drop", {"name": "01.mp3", "data": base64.b64encode(MP3).decode()})
        self.assertEqual((st, out["missing"]), (200, []))
        self.assertTrue(any(j["kind"] == "timing_build" for j in self.jobs.list_jobs()))

    def test_add_language(self):
        st, out = self.req("POST", "/api/projects/001-a/languages", {"add": "de"})
        self.assertEqual(st, 200)
        self.assertEqual(out["languages"], ["vi", "en", "de"])
        for sub in ("script", "audio", "render", "upload"):
            self.assertTrue(os.path.isdir(os.path.join(self.pdir, "lang", "de", sub)))
        self.assertEqual(self.req("POST", "/api/projects/001-a/languages", {"add": "de"})[0], 400)
        self.assertEqual(self.req("POST", "/api/projects/001-a/languages", {"add": "xx"})[0], 400)
        self.assertEqual(self.req("POST", "/api/projects/001-a/languages", {"add": ["../x"]})[0], 400)
        self.assertEqual(self.req("GET", "/api/projects/001-a/langs/de")[0], 200)

    def test_thumb_and_upload_texts_refuse_bad_input(self):
        st, out = self.req("POST", "/api/projects/001-a/langs/en/thumb", {"bg": "BG01", "hero": "x/y.z", "title": "T"})
        self.assertEqual(st, 400)
        st, out = self.req("POST", "/api/projects/001-a/langs/en/upload_texts", {})
        self.assertEqual(st, 400)
        self.assertEqual(self.req("GET", "/api/projects/001-a/langs/en/thumb.png")[0], 404)


if __name__ == "__main__":
    unittest.main()
