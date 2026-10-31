"""Languages tab API (Plan 6). studio/server.py appends ROUTES; same (method, pattern, fn) format.

  GET  /api/projects/<id>/langs/<lang>                  {source, script, check, outline, facts, voice, timing, upload, render, thumb}
  POST /api/projects/<id>/langs/<lang>/rewrite          agy_rewrite job
  POST /api/projects/<id>/langs/<lang>/review           claude_review_lang job
  POST /api/projects/<id>/langs/<lang>/approve          owner approval
  POST /api/projects/<id>/langs/<lang>/voice/prepare    part texts + parts.json
  GET  /api/projects/<id>/langs/<lang>/voice/parts/NN.txt
  POST /api/projects/<id>/langs/<lang>/voice/drop       {"name": "01.mp3", "data": base64}
  POST /api/projects/<id>/langs/<lang>/upload_texts     agy_upload_texts job
  POST /api/projects/<id>/langs/<lang>/thumb            {"bg", "hero", "title"} -> render_thumb job
  GET  /api/projects/<id>/langs/<lang>/thumb.png
  POST /api/projects/<id>/languages                     {"add": "de"}
The render button posts to Plan 5's /api/projects/<id>/render/<lang>.
"""
import base64
import binascii
import glob
import os

from studio import server as S
from tools.longform import factbank, langscript, project, script, upload, voice

MAX_MP3_B64 = 70 * 1024 * 1024


def _lang(pid, lang):
    pdir = S.project_dir(pid)
    S.lang_or_404(lang)
    meta = project.load_project(pdir)
    if lang not in meta["languages"]:
        raise S.HttpError(404, "dự án không có ngôn ngữ %s" % lang)
    return pdir, lang == meta.get("source_lang", "vi")


def _call(fn, *args):
    try:
        return fn(*args)
    except ValueError as e:
        raise S.HttpError(400, str(e))


def get_lang(q, body, pid, lang):
    pdir, source = _lang(pid, lang)
    data = script.load(pdir, lang)
    if source:
        check = {"report": script.report(pdir), "problems": [], "per_sentence": {}, "glossary_misses": 0}
    else:
        check = langscript.check(pdir, lang) if data else None
    try:
        outline = langscript.outline(pdir)
    except ValueError:
        outline = None
    ids = {f for b in outline or [] for f in b["facts"]}
    facts = {f["id"]: {"claim": f.get("claim", ""), "status": f["status"]} for f in factbank.load(pdir)[1].values() if f["id"] in ids}
    timing = upload.load_timing(pdir, lang)
    renders = sorted(os.path.basename(p) for p in glob.glob(os.path.join(pdir, "lang", lang, "render", "*.mp4")))
    up = upload.load(pdir, lang)
    return {"lang": lang, "source": source, "script": data, "check": check, "outline": outline, "facts": facts,
            "voice": voice.status(pdir, lang), "timing": bool(timing), "duration": (timing or {}).get("duration"),
            "upload": up, "chapters": upload.chapters(pdir, lang), "render": renders,
            "thumb": os.path.isfile(os.path.join(pdir, "lang", lang, "upload", "thumb.png"))}


def _job(kind, label):
    def fn(q, body, pid, lang):
        _lang(pid, lang)
        return S._enqueue(kind, {"project": pid, "lang": lang}, pid, "%s %s" % (label, lang.upper()))
    return fn


def approve(q, body, pid, lang):
    pdir, _ = _lang(pid, lang)
    return _call(script.approve, pdir, "owner", lang)


def voice_prepare(q, body, pid, lang):
    pdir, _ = _lang(pid, lang)
    return _call(voice.prepare, pdir, lang)


def voice_part(q, body, pid, lang, part):
    pdir, _ = _lang(pid, lang)
    try:
        path = voice.part_text(pdir, lang, part)
    except ValueError:
        raise S.HttpError(404, "không có phần %s" % part)
    if not os.path.isfile(path):
        raise S.HttpError(404, "không có phần %s" % part)
    return S.TextReply(path)


def voice_drop(q, body, pid, lang):
    pdir, _ = _lang(pid, lang)
    name, data = body.get("name"), body.get("data")
    if not isinstance(name, str) or not isinstance(data, str) or len(data) > MAX_MP3_B64:
        raise S.HttpError(400, "cần name và data (base64, tối đa 50 MB)")
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        raise S.HttpError(400, "data không phải base64")
    return _call(voice.drop, pdir, lang, name, raw)


def make_thumb(q, body, pid, lang):
    _lang(pid, lang)
    params = {"project": pid, "lang": lang, "bg": body.get("bg"), "hero": body.get("hero"), "title": body.get("title")}
    return S._enqueue("render_thumb", params, pid, "Thumbnail %s" % lang.upper())


def thumb_png(q, body, pid, lang):
    pdir, _ = _lang(pid, lang)
    path = os.path.join(pdir, "lang", lang, "upload", "thumb.png")
    if not os.path.isfile(path):
        raise S.HttpError(404, "chưa có thumbnail")
    return S.FileReply(path)


def add_language(q, body, pid):
    pdir = S.project_dir(pid)
    return {"languages": _call(project.add_language, pdir, body.get("add"))}


LANG = r"/api/projects/([^/]+)/langs/([a-z]{2,3})"
ROUTES = [
    ("GET", LANG, get_lang),
    ("POST", LANG + r"/rewrite", _job("agy_rewrite", "agy viết lại")),
    ("POST", LANG + r"/review", _job("claude_review_lang", "Claude soát")),
    ("POST", LANG + r"/approve", approve),
    ("POST", LANG + r"/voice/prepare", voice_prepare),
    ("GET", LANG + r"/voice/parts/(\d{2})\.txt", voice_part),
    ("POST", LANG + r"/voice/drop", voice_drop),
    ("POST", LANG + r"/upload_texts", _job("agy_upload_texts", "agy viết text upload")),
    ("POST", LANG + r"/thumb", make_thumb),
    ("GET", LANG + r"/thumb\.png", thumb_png),
    ("POST", r"/api/projects/([^/]+)/languages", add_language),
]
