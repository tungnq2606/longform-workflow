"""Studio: the owner's dashboard for long-form videos.

  .venv/bin/python -m studio          then open http://127.0.0.1:8765

Listens on 127.0.0.1 only. Every request must carry our own Host (blocks DNS rebinding); every POST must be JSON and,
when the browser sends an Origin, our own Origin (blocks other sites from starting jobs). The browser never sends a
command: it names a job kind, and the kind builds the argv.
"""
import base64
import binascii
import json
import os
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tools.longform import (castsheet, chat, claude_box, factbank, images, inbox, jobs, languages, library_index, paths,
                            progress, project, script, stylebook, workers)

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
HEX_ID = re.compile(r"^[0-9a-f]{32}$")
MAX_UPLOAD = 30 * 1024 * 1024
UPLOAD_TYPES = (".pdf", ".jpg", ".jpeg", ".png", ".txt")
MAX_LANE = 8
FACTIONS_TS = os.path.join(paths.WS, "tools", "anim", "src", "longform", "factions.ts")
FACTION_LINE = re.compile(r"^\s*([a-z][a-z0-9_]*):\s*\{(.*)\},?\s*$")
FACTION_FIELD = re.compile(r"([a-z]+):\s*'?([^,'}]*)'?")
RUNNER = None  # the live jobs.Runner (set by main), so lane changes apply at once
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


class TextReply(FileReply):
    pass


def thumb(q, body, kind, item):
    try:
        return FileReply(library_index.thumb(kind, item))
    except KeyError:
        raise HttpError(404, "không có ảnh")


def inbox_done(q, body, iid):
    if not HEX_ID.match(iid):
        raise HttpError(404, "không có việc này")
    return {"ok": inbox.resolve(iid)}


# ---------------------------------------------------------------- script step (Plan 3)
def get_facts(q, body, pid):
    sources, facts = factbank.load(project_dir(pid))
    return {"sources": sources, "facts": facts}


def get_page(q, body, pid, num):
    pdir = project_dir(pid)
    rel = "research/pages/%s.txt" % num
    sources, facts = factbank.load(pdir)
    known = {s.get("page_file") for s in sources.values()} | {f.get("page_file") for f in facts.values()}
    if not re.fullmatch(r"\d{3}", num) or rel not in known or not os.path.isfile(os.path.join(pdir, rel)):
        raise HttpError(404, "không có trang này")
    return TextReply(os.path.join(pdir, rel))


def get_script(q, body, pid):
    pdir = project_dir(pid)
    return {"script": script.load(pdir), "report": script.report(pdir)}


def set_sentence(q, body, pid):
    pdir = project_dir(pid)
    edit = [{"op": "set", "id": body.get("id"), "text": body.get("text"), "facts": body.get("facts") or []}]
    allowed = {f["id"] for f in factbank.load(pdir)[1].values() if f["status"] != "rejected"}  # pending shows red
    try:
        return {"version": script.update(pdir, lambda cur: chat.apply_edits(cur, edit, allowed, reviewed=None), "owner")}
    except ValueError as e:
        raise HttpError(400, str(e))


def approve_script(q, body, pid):
    try:
        return script.approve(project_dir(pid), "owner")
    except ValueError as e:
        raise HttpError(400, str(e))


def _enqueue(kind, params, pid, label):
    try:
        return jobs.enqueue(kind, params, pid, label)
    except ValueError as e:
        raise HttpError(400, str(e))


def start_research(q, body, pid):
    project_dir(pid)
    return _enqueue("agy_research", {"project": pid, "request": body.get("request")}, pid, "agy tìm tư liệu: %s" % str(body.get("request"))[:60])


def start_draft(q, body, pid):
    project_dir(pid)
    return _enqueue("agy_draft", {"project": pid, "request": body.get("request")}, pid, "agy viết nháp: %s" % str(body.get("request"))[:60])


def start_review(q, body, pid):
    project_dir(pid)
    return _enqueue("claude_review", {"project": pid}, pid, "Claude soát kịch bản")


def post_chat(q, body, pid):
    project_dir(pid)
    return _enqueue("agy_chat", {"project": pid, "message": body.get("message")}, pid, "agy chat: %s" % str(body.get("message"))[:60])


def get_chat(q, body, pid):
    return chat.history(project_dir(pid))


def fact_status(q, body, pid, fid):
    pdir = project_dir(pid)
    try:
        f = factbank.set_status(pdir, fid, body.get("status"), "owner", str(body.get("note") or ""))
        script.recheck_approval(pdir)
        return f
    except KeyError:
        raise HttpError(404, "không có dữ kiện %s" % fid)
    except ValueError as e:
        raise HttpError(400, str(e))


def upload_source(q, body, pid):
    pdir = project_dir(pid)
    name = os.path.basename(str(body.get("name") or ""))
    ext = os.path.splitext(name)[1].lower()
    if ext not in UPLOAD_TYPES:
        raise HttpError(400, "chỉ nhận PDF, JPG, PNG, TXT")
    try:
        data = base64.b64decode(body.get("data") or "", validate=True)
    except (binascii.Error, TypeError):
        raise HttpError(400, "dữ liệu file hỏng")
    if not data or len(data) > MAX_UPLOAD:
        raise HttpError(400, "file trống hoặc lớn quá 30 MB")
    up = os.path.join(pdir, "research", "uploads")
    os.makedirs(up, exist_ok=True)
    stem = project.ascii_slug(os.path.splitext(name)[0]) or "file"
    target, n = os.path.join(up, stem + ext), 1
    while os.path.exists(target):
        n += 1
        target = os.path.join(up, "%s-%d%s" % (stem, n, ext))
    with open(target, "wb") as f:
        f.write(data)
    request = ("Rút dữ kiện từ file chủ kênh tải lên: %s (đọc file này; url = 'file:%s'; page_file = bản chép lại nội dung "
               "trang có đoạn trích, ghi số trang vào location)." % (target, os.path.basename(target)))
    return _enqueue("agy_research", {"project": pid, "request": request}, pid, "agy đọc file %s" % os.path.basename(target))


def lang_or_404(lang):
    if lang not in languages.load_languages():
        raise HttpError(404, "không có ngôn ngữ %s" % lang)
    return lang


def get_stylebook(q, body, lang):
    return stylebook.load(lang_or_404(lang))


def decide_rule(q, body, lang, rid):
    try:
        return stylebook.decide(lang_or_404(lang), rid, bool(body.get("keep")))
    except KeyError:
        raise HttpError(404, "không có quy tắc %s" % rid)


# ---------------------------------------------------------------- images step (Plan 4)
def _lanes():
    return dict(RUNNER.lanes) if RUNNER is not None else dict(studio_config()["lanes"])


def get_images(q, body, pid):
    pdir = project_dir(pid)
    return {"items": images.load(pdir), "counts": images.counts(pdir), "lanes": _lanes()}


def _item_call(fn, pdir, iid, *args):
    try:
        return fn(pdir, iid, *args)
    except KeyError:
        raise HttpError(404, "không có ảnh %s" % iid)
    except ValueError as e:
        raise HttpError(400, str(e))


def image_file(q, body, pid, iid, which):
    pdir = project_dir(pid)
    try:
        return FileReply(images.thumb(pdir, iid) if which == "thumb" else images.file_of(pdir, iid, which))
    except KeyError:
        raise HttpError(404, "không có ảnh")


def image_action(q, body, pid, iid, action):
    pdir = project_dir(pid)
    if action == "approve":
        return _item_call(images.approve, pdir, iid)
    if action == "reject":
        return _item_call(images.reject, pdir, iid)
    if action == "redo":
        note = body.get("note")
        if not isinstance(note, str) or len(note) > 2000:
            raise HttpError(400, "ghi chú không hợp lệ")
        return _item_call(images.redo, pdir, iid, note)
    if action == "to_library":
        return {"id": _item_call(images.save_background, pdir, iid, body.get("name"))}
    raise HttpError(404, "không có")


def approve_many(q, body, pid):
    ids = body.get("ids")
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise HttpError(400, "danh sách ảnh không hợp lệ")
    return images.approve_many(project_dir(pid), ids)


def start_shotlist(q, body, pid):
    project_dir(pid)
    return _enqueue("agy_shotlist", {"project": pid}, pid, "agy lập danh sách ảnh")


def build_cast_sheet(q, body, pid):
    try:
        castsheet.build(project_dir(pid))
    except ValueError as e:
        raise HttpError(400, str(e))
    return {"ok": True}


def get_cast_sheet(q, body, pid):
    path = os.path.join(project_dir(pid), "images", "cast_sheet.png")
    if not os.path.isfile(path):
        raise HttpError(404, "chưa có ảnh tổng nhân vật")
    return FileReply(path)


def set_lanes(q, body):
    n = body.get("agy")
    if type(n) is not int or not 1 <= n <= MAX_LANE:
        raise HttpError(400, "số luồng agy phải từ 1 đến %d" % MAX_LANE)
    if RUNNER is not None:
        RUNNER.lanes["agy"] = n
    cfg = studio_config()
    cfg["lanes"]["agy"] = n
    p = os.path.join(paths.config(), "studio.json")
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    os.replace(p + ".tmp", p)
    return {"agy": n}


def library_factions(q, body):
    """Crowd factions, read-only, parsed from the Remotion source (the only place they are defined)."""
    out, inside = [], False
    with open(FACTIONS_TS, encoding="utf-8") as f:
        for line in f:
            if line.startswith("export const FACTIONS"):
                inside = True
                continue
            if inside and line.startswith("}"):
                break
            m = FACTION_LINE.match(line) if inside else None
            if m:
                out.append(dict([("id", m.group(1))] + [(k, v.strip()) for k, v in FACTION_FIELD.findall(m.group(2))]))
    return out


def library_kits(q, body):
    return library_index.kits()


def new_pose(q, body, kit_id):
    if kit_id not in {k["id"] for k in library_index.kits()}:
        raise HttpError(404, "không có bộ nhân vật %s" % kit_id)
    pid = body.get("project")
    if not isinstance(pid, str):
        raise HttpError(400, "chọn dự án cho tư thế mới")
    pdir = project_dir(pid)
    key = body.get("pose_key")
    if key in {p["key"] for k in library_index.kits() if k["id"] == kit_id for p in k["poses"]}:
        raise HttpError(400, "bộ %s đã có tư thế %s" % (kit_id, key))
    spec = body.get("spec")
    if spec is None:
        desc = body.get("description")
        if not isinstance(desc, str) or not desc.strip() or len(desc) > 1000:
            raise HttpError(400, "thiếu mô tả tư thế")
        spec = {"shot": "full body", "angle": "eye level", "layout": "one figure centred, feet near the bottom edge",
                "setting": "plain flat chroma green #00B140, nothing else", "people": desc.strip(),
                "props": "only what the model sheet shows", "light": "flat even light",
                "must_not": ["second figure", "model sheet layout", "scenery", "floor or shadow"]}
    try:
        it = images.add(pdir, "pose", spec, kit=kit_id, pose_key=key)
    except ValueError as e:
        raise HttpError(400, str(e))
    jobs.enqueue("agy_image", {"project": pid, "item": it["id"]}, pid, "agy vẽ tư thế mới %s %s" % (kit_id, key))
    return it


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
    ("GET", r"/api/projects/([^/]+)/facts", get_facts),
    ("GET", r"/api/projects/([^/]+)/pages/([^/]+)", get_page),
    ("GET", r"/api/projects/([^/]+)/script", get_script),
    ("POST", r"/api/projects/([^/]+)/script/sentence", set_sentence),
    ("POST", r"/api/projects/([^/]+)/script/approve", approve_script),
    ("POST", r"/api/projects/([^/]+)/research", start_research),
    ("POST", r"/api/projects/([^/]+)/draft", start_draft),
    ("POST", r"/api/projects/([^/]+)/review", start_review),
    ("POST", r"/api/projects/([^/]+)/chat", post_chat),
    ("GET", r"/api/projects/([^/]+)/chat", get_chat),
    ("POST", r"/api/projects/([^/]+)/facts/([^/]+)/status", fact_status),
    ("POST", r"/api/projects/([^/]+)/sources/upload", upload_source),
    ("GET", r"/api/stylebook/([^/]+)", get_stylebook),
    ("POST", r"/api/stylebook/([^/]+)/([^/]+)/decide", decide_rule),
    ("GET", r"/api/projects/([^/]+)/images", get_images),
    ("POST", r"/api/projects/([^/]+)/images/approve_many", approve_many),
    ("GET", r"/api/projects/([^/]+)/images/([A-Z]+[0-9]+)/(raw|final|cutout|thumb)", image_file),
    ("POST", r"/api/projects/([^/]+)/images/([A-Z]+[0-9]+)/(approve|redo|reject|to_library)", image_action),
    ("POST", r"/api/projects/([^/]+)/shotlist", start_shotlist),
    ("POST", r"/api/projects/([^/]+)/cast_sheet", build_cast_sheet),
    ("GET", r"/api/projects/([^/]+)/cast_sheet", get_cast_sheet),
    ("POST", r"/api/lanes", set_lanes),
    ("GET", r"/api/library/kits", library_kits),
    ("GET", r"/api/library/factions", library_factions),
    ("POST", r"/api/library/kits/([^/]+)/new_pose", new_pose),
]
ROUTES += __import__("studio.routes_langs", fromlist=["ROUTES"]).ROUTES  # Plan 6: languages tab (studio/routes_langs.py)
from studio import routes_scenes; ROUTES += routes_scenes.ROUTES  # noqa: E402,E702  Plan 5 scene board


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
                    if isinstance(out, TextReply):
                        with open(out.path, "rb") as f:
                            return self._send(200, f.read(), "text/plain; charset=utf-8")
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
    global RUNNER
    runner = jobs.Runner(cfg["lanes"])
    srv.runner = RUNNER = runner
    runner.start()
    print("Studio: http://127.0.0.1:%d" % cfg["port"], flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        runner.stop()
        srv.server_close()
