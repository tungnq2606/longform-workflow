"""Scene board API (Plan 5), added to studio/server.py ROUTES.

  GET  /api/projects/<id>/scenes                 scene file, problems, labels, previews, timing per language, renders
  POST /api/projects/<id>/scenes/write           job claude_scenes (Claude writes the scene file)
  POST /api/projects/<id>/scenes/beat/<B>        {"sfx": [...], "music": id|null}: the owner edits sound (validated)
  POST /api/projects/<id>/scenes/preview/<B>     job render_still
  GET  /api/projects/<id>/scenes/preview/<B>     the preview PNG
  POST /api/projects/<id>/render/<lang>          job render_lang (refused with the reasons when not ready)
  GET  /api/audio                                the audio library index (+ problems)

Beats are looked up in the scene file, never built from the caller's text, so no path can escape the project.
"""
import json
import os
import re

from tools.longform import audio_lib, jobs, paths, project, render, scenes, script, timing

BEAT = r"(B[0-9]+)"
LANG = r"([a-z]{2,3})"


def _srv():
    from studio import server  # server imports this module: look it up at call time
    return server


def _err(code, msg):
    return _srv().HttpError(code, msg)


def _pdir(pid):
    return _srv().project_dir(pid)


def _beat(pdir, bid):
    cur = scenes.load(pdir)
    if not cur or bid not in cur.get("beats", {}):
        raise _err(404, "không có cảnh %s" % bid)
    return cur


def _active(pid, kind, key, value):
    return any(j["kind"] == kind and j["project"] == pid and j["status"] in ("queued", "running") and j["params"].get(key) == value
               for j in jobs.list_jobs(500))


def _render_state(pdir, pid, lang):
    problems = render.check(pdir, lang)
    out = render.output_path(pdir, lang)
    state = {"problems": problems, "file": os.path.relpath(out, paths.root()) if os.path.isfile(out) else None}
    if _active(pid, "render_lang", "lang", lang):
        state["state"] = "rendering"
    elif timing.load(pdir, lang) is None:
        state["state"] = "missing_timing"
    elif problems:
        state["state"] = "blocked"
    else:
        state["state"] = "done" if state["file"] else "ready"
    return state


def _script_rows(pdir):
    rows = []
    for ch in (script.load(pdir) or {}).get("chapters", []):
        for b in ch.get("beats", []):
            rows.append({"id": b["id"], "chapter": ch["id"], "goal": b.get("goal", ""),
                         "sentences": [{"id": s["id"], "text": s["text"]} for s in b.get("sentences", [])]})
    return rows


def _bg_thumbs(pid, doc):
    out = {}
    for b in (doc or {}).get("beats", {}).values():
        ref = str((b.get("background") or {}).get("id") or "")
        kind, _, ident = ref.partition(":")
        if kind == "library":
            out[ref] = "/api/thumb/bg/%s" % ident
        elif kind == "project":
            out[ref] = "/api/projects/%s/images/%s/thumb" % (pid, ident)
    return out


def _mtime(path):
    return int(os.path.getmtime(path)) if os.path.isfile(path) else False


def get_scenes(q, body, pid):
    pdir = _pdir(pid)
    doc = scenes.load(pdir)
    langs = project.load_project(pdir)["languages"]
    beats = list((doc or {}).get("beats", {}))
    return {"scenes": doc, "problems": scenes.validate(pdir, doc) if doc else [], "labels": scenes.labels(pdir),
            "previews": {b: _mtime(render.preview_path(pdir, b)) for b in beats},  # mtime busts the image cache
            "previewing": [b for b in beats if _active(pid, "render_still", "beat", b)],
            "timing": {l: timing.load(pdir, l) is not None for l in langs},
            "renders": {l: _render_state(pdir, pid, l) for l in langs} if doc else {},
            "warnings": render.warnings(pdir), "script": _script_rows(pdir), "bg_thumbs": _bg_thumbs(pid, doc),
            "writing": _active(pid, "claude_scenes", "project", pid)}


def write_scenes(q, body, pid):
    _pdir(pid)
    try:
        return jobs.enqueue("claude_scenes", {"project": pid}, pid, "Claude dựng cảnh")
    except ValueError as e:
        raise _err(400, str(e))


def edit_beat(q, body, pid, bid):
    pdir = _pdir(pid)
    cur = _beat(pdir, bid)
    new = json.loads(json.dumps(cur))
    if "sfx" in body:
        if not isinstance(body["sfx"], list):
            raise _err(400, "sfx phải là danh sách")
        new["beats"][bid]["sfx"] = body["sfx"]
    if "music" in body:
        chapter = next((r["chapter"] for r in _script_rows(pdir) if r["id"] == bid), None)
        for ch in new.get("chapters") or []:
            if ch.get("id") == chapter:
                ch["music"] = body["music"]
    problems = [p for p in scenes.validate(pdir, new) if p.startswith(bid + ":") or re.match(r"C\d+: ", p)]
    if problems:
        raise _err(400, "; ".join(problems))
    try:
        v = scenes.save(pdir, {k: v for k, v in new.items() if k not in ("version", "updated_by", "updated_at")}, "owner",
                        base=cur["version"])
    except ValueError as e:
        raise _err(409, str(e))
    return {"version": v}


def preview(q, body, pid, bid):
    pdir = _pdir(pid)
    _beat(pdir, bid)
    try:
        return jobs.enqueue("render_still", {"project": pid, "beat": bid}, pid, "Xem trước %s" % bid)
    except ValueError as e:
        raise _err(400, str(e))


def preview_file(q, body, pid, bid):
    pdir = _pdir(pid)
    _beat(pdir, bid)
    path = render.preview_path(pdir, bid)
    if not os.path.isfile(path):
        raise _err(404, "chưa có ảnh xem trước %s" % bid)
    return _srv().FileReply(path)


def render_lang(q, body, pid, lang):
    pdir = _pdir(pid)
    if lang not in project.load_project(pdir)["languages"]:
        raise _err(400, "dự án không có ngôn ngữ %s" % lang)
    problems = render.check(pdir, lang)
    if problems:
        raise _err(400, "; ".join(problems))
    if _active(pid, "render_lang", "lang", lang):
        raise _err(400, "đang render %s" % lang)
    return jobs.enqueue("render_lang", {"project": pid, "lang": lang}, pid, "Render %s" % lang.upper())


def audio(q, body):
    return dict(audio_lib.load(), problems=audio_lib.problems())


ROUTES = [
    ("GET", r"/api/projects/([^/]+)/scenes", get_scenes),
    ("POST", r"/api/projects/([^/]+)/scenes/write", write_scenes),
    ("POST", r"/api/projects/([^/]+)/scenes/beat/" + BEAT, edit_beat),
    ("POST", r"/api/projects/([^/]+)/scenes/preview/" + BEAT, preview),
    ("GET", r"/api/projects/([^/]+)/scenes/preview/" + BEAT, preview_file),
    ("POST", r"/api/projects/([^/]+)/render/" + LANG, render_lang),
    ("GET", r"/api/audio", audio),
]
