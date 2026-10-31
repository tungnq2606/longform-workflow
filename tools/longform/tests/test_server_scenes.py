"""Scene board API (Plan 5): studio/routes_scenes.py on a live Studio server bound to a temp root."""
import http.client
import json
import os
import threading

from tools.longform.tests.scenefix import SceneBase, labels_doc


class ServerScenesTest(SceneBase):
    def setUp(self):
        super().setUp()
        from studio import server
        self.kinds = dict(self.jobs.KINDS)
        self.srv = server.make_server(0, None)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.approve_script()
        self.approve_image()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.jobs.KINDS.clear()
        self.jobs.KINDS.update(self.kinds)
        super().tearDown()

    def req(self, method, path, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        h = {"Host": "127.0.0.1:%d" % self.port}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        raw = r.read()
        ctype = r.getheader("Content-Type")
        c.close()
        try:
            return r.status, json.loads(raw)
        except ValueError:
            return r.status, (ctype, raw)

    def save(self, doc=None):
        self.scenes.save(self.pdir, doc or self.doc(), "claude", labels=labels_doc())

    def test_scenes_endpoint(self):
        st, d = self.req("GET", "/api/projects/001-a/scenes")
        self.assertEqual(st, 200)
        self.assertIsNone(d["scenes"])
        self.save()
        st, d = self.req("GET", "/api/projects/001-a/scenes")
        self.assertEqual(d["scenes"]["version"], 1)
        self.assertEqual(d["problems"], [])
        self.assertEqual(d["labels"]["date_1288"]["vi"], "Năm 1288")
        self.assertEqual(d["previews"], {"B01": False})
        self.assertEqual(d["timing"], {"vi": False})
        self.assertEqual(d["renders"]["vi"]["state"], "missing_timing")
        self.assertEqual([b["id"] for b in d["script"]], ["B01"])
        self.assertEqual(d["script"][0]["sentences"][0]["id"], "s001")
        self.assertEqual(d["bg_thumbs"]["library:river-01"], "/api/thumb/bg/river-01")
        st, a = self.req("GET", "/api/audio")
        self.assertEqual([e["id"] for e in a["sfx"]], ["oar-01"])
        self.assertEqual(self.req("GET", "/api/projects/../scenes")[0], 404)

    def test_write_queues_claude_scenes(self):
        st, j = self.req("POST", "/api/projects/001-a/scenes/write", {})
        self.assertEqual((st, j["kind"]), (200, "claude_scenes"))
        self.approve_script(approved=False)
        st, e = self.req("POST", "/api/projects/001-a/scenes/write", {})
        self.assertEqual(st, 400)
        self.assertIn("chốt", e["error"])

    def test_beat_sound_edit_validated(self):
        self.save()
        st, e = self.req("POST", "/api/projects/001-a/scenes/beat/B01", {"sfx": [{"sentence": "s001", "id": "laser-01", "offset": 0, "gain": 0.3}]})
        self.assertEqual(st, 400)
        self.assertIn("laser-01", e["error"])
        self.assertEqual(self.scenes.load(self.pdir)["version"], 1)
        st, e = self.req("POST", "/api/projects/001-a/scenes/beat/B01", {"sfx": "x"})
        self.assertEqual(st, 400)
        st, d = self.req("POST", "/api/projects/001-a/scenes/beat/B01",
                         {"sfx": [{"sentence": "s001", "id": "oar-01", "offset": 0.5, "gain": 0.3}], "music": None})
        self.assertEqual(st, 200)
        cur = self.scenes.load(self.pdir)
        self.assertEqual((cur["version"], cur["updated_by"]), (2, "owner"))
        self.assertEqual(cur["beats"]["B01"]["sfx"], [{"sentence": "s001", "id": "oar-01", "offset": 0.5, "gain": 0.3}])
        self.assertIsNone(cur["chapters"][0]["music"])
        st, e = self.req("POST", "/api/projects/001-a/scenes/beat/B01", {"music": "pop-01"})
        self.assertEqual(st, 400)
        self.assertEqual(self.req("POST", "/api/projects/001-a/scenes/beat/B09", {"sfx": []})[0], 404)

    def test_preview_route_only_known_beats(self):
        self.save()
        self.assertEqual(self.req("GET", "/api/projects/001-a/scenes/preview/B01")[0], 404)  # not made yet
        self.assertEqual(self.req("GET", "/api/projects/001-a/scenes/preview/B09")[0], 404)
        self.assertEqual(self.req("GET", "/api/projects/001-a/scenes/preview/..%2Fscript")[0], 404)
        os.makedirs(os.path.join(self.pdir, "images", "previews"))
        with open(os.path.join(self.pdir, "images", "previews", "B01.png"), "wb") as f:
            f.write(b"\x89PNG fake")
        st, (ctype, raw) = self.req("GET", "/api/projects/001-a/scenes/preview/B01")
        self.assertEqual((st, ctype, raw), (200, "image/png", b"\x89PNG fake"))
        st, j = self.req("POST", "/api/projects/001-a/scenes/preview/B01", {})
        self.assertEqual((st, j["kind"], j["params"]["beat"]), (200, "render_still", "B01"))
        self.assertEqual(self.req("POST", "/api/projects/001-a/scenes/preview/B09", {})[0], 404)

    def test_render_route_refuses_until_ready(self):
        self.save()
        st, e = self.req("POST", "/api/projects/001-a/render/vi", {})
        self.assertEqual(st, 400)
        self.assertIn("giọng", e["error"])
        self.assertEqual(self.req("POST", "/api/projects/001-a/render/xx", {})[0], 400)
