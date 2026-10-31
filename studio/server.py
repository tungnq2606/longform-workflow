"""Studio: the owner's dashboard for long-form videos.

  .venv/bin/python -m studio          then open http://127.0.0.1:8765

Listens on 127.0.0.1 only. Every request must carry our own Host (blocks DNS rebinding); every POST must be JSON and,
when the browser sends an Origin, our own Origin (blocks other sites from starting jobs). The browser never sends a
command: it names a job kind, and the kind builds the argv.
"""
import json
import os
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tools.longform import claude_box, inbox, jobs, languages, library_index, paths, progress, project

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
HEX_ID = re.compile(r"^[0-9a-f]{32}$")
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".json": "application/json"}


class HttpError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


def studio_config():
    with open(os.path.join(paths.config(), "studio.json"), encoding="utf-8") as f:
        return json.load(f)


def project_dir(pid):
    try:
        claude_box.check_project(pid)
    except ValueError:
        raise HttpError(404, "không có dự án %s" % pid)
    return os.path.join(paths.projects(), pid)


def project_card(meta):
    g = progress.get(os.path.join(paths.projects(), meta["id"]))
    return {"id": meta["id"], "title": meta["title"], "languages": meta["languages"], "done": g["done"], "total": g["total"],
            "steps": [s["state"] for s in g["steps"]]}


def home(q, body):
    return {"inbox": inbox.open_items(), "projects": [project_card(m) for m in project.list_projects()], "paused": jobs.paused(),
            "library": library_index.summary()}


def langs(q, body):
    return [{"code": l.code, "name": l.name} for l in languages.load_languages().values()]


def new_project(q, body):
    title = body.get("title")
    if not isinstance(title, str) or not title.strip():
        raise HttpError(400, "thiếu tên video")
    codes = body.get("languages") or []
    if not isinstance(codes, list) or not all(isinstance(c, str) for c in codes):
        raise HttpError(400, "danh sách ngôn ngữ không hợp lệ")
    try:
        d = project.new_project(title.strip(), codes)
    except (ValueError, FileExistsError) as e:
        raise HttpError(400, str(e))
    return {"id": os.path.basename(d)}


def get_project(q, body, pid):
    d = project_dir(pid)
    return {"project": project.load_project(d), "progress": progress.get(d), "inbox": inbox.open_items(pid)}


def job_or_404(jid):
    if not HEX_ID.match(jid) or not jobs.get(jid):
        raise HttpError(404, "không có job")
    return jid


def job_log(q, body, jid):
    try:
        offset = max(0, int(q.get("offset", ["0"])[0]))
    except ValueError:
        offset = 0
    text, off = jobs.read_log(job_or_404(jid), offset)
    return {"text": text, "offset": off}


def stop_job(q, body, jid):
    return {"ok": jobs.stop(job_or_404(jid))}


def pause(q, body):
    on = bool(body.get("on"))
    jobs.set_paused(on, "Bạn bấm Tạm dừng" if on else "")
    return jobs.paused()


def claude(q, body):
    pid = body.get("project") or None
    if pid is not None:
        project_dir(pid)
    try:
        return jobs.enqueue("claude", {"message": body.get("message"), "project": pid, "model": body.get("model")}, pid,
                            "Claude: %s" % str(body.get("message") or "")[:60])
    except ValueError as e:
        raise HttpError(400, str(e))


def claude_history(q, body):
    pid = q.get("project", [None])[0] or None
    if pid is not None:
        project_dir(pid)
    return claude_box.history(pid)


def claude_models(q, body):
    return studio_config()["claude"]["models"]


class FileReply:
    def __init__(self, path):
        self.path = path


def thumb(q, body, kind, item):
    try:
        return FileReply(library_index.thumb(kind, item))
    except KeyError:
        raise HttpError(404, "không có ảnh")


def inbox_done(q, body, iid):
    if not HEX_ID.match(iid):
        raise HttpError(404, "không có việc này")
    return {"ok": inbox.resolve(iid)}


ROUTES = [
    ("GET", r"/api/home", home),
    ("GET", r"/api/languages", langs),
    ("POST", r"/api/projects", new_project),
    ("GET", r"/api/projects/([^/]+)", get_project),
    ("GET", r"/api/jobs", lambda q, body: jobs.list_jobs()),
    ("GET", r"/api/jobs/([^/]+)/log", job_log),
    ("POST", r"/api/jobs/([^/]+)/stop", stop_job),
    ("POST", r"/api/pause", pause),
    ("POST", r"/api/claude", claude),
    ("GET", r"/api/claude/history", claude_history),
    ("GET", r"/api/claude/models", claude_models),
    ("POST", r"/api/inbox/([^/]+)/done", inbox_done),
    ("GET", r"/api/thumb/([a-z]+)/([^/]+)", thumb),
]


class Handler(BaseHTTPRequestHandler):
    server_version = "Studio"

    def log_message(self, *a):
        pass

    def _send(self, code, data, ctype="application/json", cache="no-store"):
        raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(raw)

    def _guard(self):
        port = self.server.server_address[1]
        if self.headers.get("Host") not in ("127.0.0.1:%d" % port, "localhost:%d" % port):
            return False
        if self.command == "POST":
            origin = self.headers.get("Origin")
            if origin is not None and origin not in ("http://127.0.0.1:%d" % port, "http://localhost:%d" % port):
                return False
            if not (self.headers.get("Content-Type") or "").startswith("application/json"):
                return False
        return True

    def _static(self, rel):
        rel = urllib.parse.unquote(rel)
        base = os.path.realpath(STATIC)
        path = os.path.realpath(os.path.join(base, rel))
        if not path.startswith(base + os.sep) or not os.path.isfile(path):
            return self._send(404, {"error": "không có"})
        with open(path, "rb") as f:
            self._send(200, f.read(), TYPES.get(os.path.splitext(path)[1], "application/octet-stream"))

    def _handle(self):
        if not self._guard():
            return self._send(403, {"error": "bị chặn"})
        url = urllib.parse.urlsplit(self.path)
        if self.command == "GET" and url.path == "/":
            return self._static("index.html")
        if self.command == "GET" and url.path.startswith("/static/"):
            return self._static(url.path[len("/static/"):])
        body = {}
        if self.command == "POST":
            n = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(n) or b"{}") if n else {}
            except ValueError:
                return self._send(400, {"error": "JSON hỏng"})
            if not isinstance(body, dict):
                return self._send(400, {"error": "JSON phải là object"})
        q = urllib.parse.parse_qs(url.query)
        for method, pattern, fn in ROUTES:
            m = re.fullmatch(pattern, url.path)
            if method == self.command and m:
                try:
                    out = fn(q, body, *[urllib.parse.unquote(g) for g in m.groups()])
                    if isinstance(out, FileReply):
                        with open(out.path, "rb") as f:
                            return self._send(200, f.read(), TYPES.get(os.path.splitext(out.path)[1], "application/octet-stream"),
                                              cache="private, max-age=3600")
                    return self._send(200, out)
                except HttpError as e:
                    return self._send(e.code, {"error": e.message})
                except Exception as e:  # noqa: BLE001  one broken file must not drop the connection
                    return self._send(500, {"error": "lỗi trong Studio: %s" % e})
        return self._send(404, {"error": "không có"})

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()


def make_server(port, runner):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.daemon_threads = True
    srv.runner = runner
    return srv


def main():
    cfg = studio_config()
    srv = make_server(cfg["port"], None)  # bind first: a second Studio fails here, before touching the live one's jobs
    n = jobs.recover()
    if n:
        print("Studio: %d job bị ngắt từ lần trước (xem Cần bạn)" % n, flush=True)
    runner = jobs.Runner(cfg["lanes"])
    srv.runner = runner
    runner.start()
    print("Studio: http://127.0.0.1:%d" % cfg["port"], flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        runner.stop()
        srv.server_close()
