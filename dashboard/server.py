#!/usr/bin/env python3
"""Studio dashboard: one local web page for the whole video workflow of both channels.

Run:   python3 dashboard/server.py        then open http://127.0.0.1:8765
It listens on 127.0.0.1 only, reads and writes files in this workspace, and runs the existing tools
(make_prompts.py, agy_images.py, voice_text.py, Remotion, scout.py, Claude Code) as background jobs.
"""
import csv
import fcntl
import glob
import json
import mimetypes
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASH = os.path.join(WS, "dashboard")
CFG = json.load(open(os.path.join(DASH, "config.json"), encoding="utf-8"))
JOBS_DIR = os.path.join(DASH, "jobs")
os.makedirs(JOBS_DIR, exist_ok=True)
JOBS = {}
LOCK = threading.Lock()
sys.path.insert(0, os.path.join(WS, "tools"))
import notify  # noqa: E402  Telegram, no-op until dashboard/secrets/telegram.json exists
class flowcli:  # gflow removed 2026-10-31 (all images via agy); old dashboard kept until Plan 2 replaces it
    available = staticmethod(lambda: False)
import workqueue  # noqa: E402  per-video queue on disk: owner requests are never lost
PASS = 4  # lowest Gemini review score accepted without the owner (2026-10-29; was 5): 3 asks, 1-2 redo
NOTIFY_DONE = {"render", "review_render", "generate", "review", "review_clips"}  # also report these when they finish
SLUG_RE = re.compile(r"^(?:test-)?\d{3}-[a-z0-9-]+$")


def slug_num(slug):
    m = re.search(r"(\d{3})", slug)
    return int(m.group(1)) if m else 0


def ascii_slug(text):
    t = unicodedata.normalize("NFD", (text or "").replace("đ", "d").replace("Đ", "D"))
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return t.lower()


# ---------------------------------------------------------------- helpers
def rel(p):
    return os.path.relpath(p, WS)


def safe(path):
    """Absolute path inside the workspace, or None."""
    p = os.path.realpath(os.path.join(WS, path))
    return p if p == WS or p.startswith(WS + os.sep) else None


def read(p, default=""):
    try:
        return open(p, encoding="utf-8").read()
    except OSError:
        return default


def load_json(p, default=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def channels():
    """Every channels/<id>/channel.json (a new channel only needs that folder, see templates/channel/), plus the extra
    entries in config.json (the image-workflow examples). Read on each call, so a new channel shows up without a restart."""
    out = []
    root = os.path.join(WS, "channels")
    for cid in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        c = load_json(os.path.join(root, cid, "channel.json"), None)
        if c and c.get("status", "active") != "archived":
            out.append(dict(c, id=cid, dir="channels/" + cid, videos=c.get("videos") or ("channels/%s/videos" % cid)))
    return out + CFG.get("extra_channels", [])


def research_dir(cid):
    """Channel-level research (topic scout runs, Gemini phrase ideas and topic notes): channels/<id>/research/."""
    c = channel(cid)
    return os.path.join(WS, c["dir"], "research") if c.get("dir") else os.path.join(DASH, "general", "research")


def is_shorts_ch(c):
    return bool(c and (c.get("format") == "shorts" or c.get("aspect") == "9:16"))


def is_shorts(d):
    return is_shorts_ch(channel_of(d))


def style_id(d):
    """Image style of a video: images/shots.json or images/cast.json first, then the channel default."""
    return (load_json(os.path.join(d, "images", "shots.json"), {}).get("style")
            or load_json(os.path.join(d, "images", "cast.json"), {}).get("style")
            or channel_of(d).get("style", "stickman-v1"))


def channel_of(d):
    """The channel a video folder belongs to (its channel.json), or {} for the examples."""
    root = os.path.join(WS, "channels")
    rp = os.path.relpath(d, root)
    return load_json(os.path.join(root, rp.split(os.sep)[0], "channel.json"), {}) if not rp.startswith("..") else {}


def channel(cid):
    for c in channels():
        if c["id"] == cid:
            return c
    raise KeyError("unknown channel " + cid)


def video_dir(cid, slug):
    if not SLUG_RE.match(slug):
        raise KeyError("bad video name " + slug)
    d = os.path.join(WS, channel(cid)["videos"], slug)
    if not os.path.isdir(d):
        raise KeyError("no video " + slug)
    return d


FFMPEG_DIR = os.path.join(WS, "tools", "anim", "node_modules", "@remotion", "compositor-darwin-arm64")
FFMPEG_BIN = os.path.join(FFMPEG_DIR, "ffmpeg") if os.path.exists(os.path.join(FFMPEG_DIR, "ffmpeg")) else "ffmpeg"


def mp3_seconds(p):
    try:
        out = subprocess.run(["afinfo", p], capture_output=True, text=True).stdout
        m = re.search(r"estimated duration: ([\d.]+)", out)
        if m:
            return float(m.group(1))
        err = subprocess.run([FFMPEG_BIN, "-hide_banner", "-i", p], capture_output=True, text=True,
                             env=dict(os.environ, DYLD_LIBRARY_PATH=FFMPEG_DIR)).stderr
        dm = re.search(r"Duration: (\d+):(\d+):([0-9.]+)", err)
        if dm:
            return int(dm.group(1)) * 3600 + int(dm.group(2)) * 60 + float(dm.group(3))
    except OSError:
        pass
    return None


# ---------------------------------------------------------------- video summary
def stages(d):
    s = {}
    script = read(os.path.join(d, "script", "script.txt"))
    vids = sorted(f for f in os.listdir(os.path.join(d, "render")) if f.endswith(".mp4")) if os.path.isdir(os.path.join(d, "render")) else []
    man = load_json(os.path.join(d, "images", "prompts", "manifest.json"), {}).get("items", [])
    scenes = [i for i in man if i["kind"] == "scene"]
    have = sum(os.path.exists(os.path.join(d, "images", i["save_as"])) for i in scenes)
    shots = load_json(os.path.join(d, "images", "shots.json"), {}).get("shots", [])
    up = read(os.path.join(d, "upload", "upload.txt"))

    if is_shorts(d):
        has_tl = os.path.exists(os.path.join(d, "render", "timeline.py"))
        clips = sum(os.path.exists(os.path.join(d, "clips", i["id"] + ".mp4")) for i in scenes)
        vf = any(os.path.exists(os.path.join(d, "audio", n)) for n in ("voice_full.wav", "voice_full.mp3"))
        pdir = os.path.join(d, "audio", "vbee_parts")
        parts = [f for f in os.listdir(pdir) if f.startswith(("part1.", "part2."))] if os.path.isdir(pdir) else []
        yt = read(os.path.join(d, "packaging", "youtube.txt"))
        s["script"] = "todo" if "First voice block" in script or not script.strip() else ("done" if len(script) > 300 else "draft")
        s["shots"] = "done" if (scenes or (has_tl and vids)) else ("draft" if shots else "todo")
        s["images"] = "done" if ((scenes and have == len(scenes)) or (has_tl and vids)) else ("%d/%d" % (have, len(scenes)) if scenes else "todo")
        s["clips"] = "done" if ((scenes and clips == len(scenes)) or (has_tl and vids)) else ("%d/%d" % (clips, len(scenes)) if scenes else "todo")
        s["voice"] = "done" if vf else ("parts" if parts else "todo")
        s["render"] = "done" if vids else "todo"
        s["upload"] = "ready" if ("TITLE" in yt or "=== TITLE ===" in up) else "todo"
        return s

    s["script"] = "todo" if "First voice block" in script or not script.strip() else ("done" if len(script) > 800 else "draft")
    anim = os.path.exists(os.path.join(d, "anim", "scenes.tsx")) and "REPLACE ME" not in read(os.path.join(d, "anim", "scenes.tsx"))
    s["shots"] = "done" if shots else ("anim" if anim else "todo")
    s["images"] = "done" if scenes and have == len(scenes) else ("%d/%d" % (have, len(scenes)) if scenes else ("anim" if anim else "todo"))
    tts = sorted(f for f in os.listdir(os.path.join(d, "script", "voiceover_tts")) if f.endswith(".txt")) if os.path.isdir(os.path.join(d, "script", "voiceover_tts")) else []
    mp3 = [f for f in tts if os.path.exists(os.path.join(d, "audio", f[:-4] + ".mp3"))]
    s["voice"] = "done" if tts and len(mp3) == len(tts) else ("%d/%d" % (len(mp3), len(tts)) if tts else "todo")
    s["render"] = "done" if vids else "todo"
    s["upload"] = "ready" if "=== TITLE ===" in up else "todo"
    return s


def title_of(d):
    up = read(os.path.join(d, "upload", "upload.txt"))
    m = re.search(r"=== TITLE ===\s*\n(.+)", up)
    if m:
        return m.group(1).strip()
    yt = read(os.path.join(d, "packaging", "youtube.txt"))
    m2 = re.search(r"^TITLE \(chosen\)\s*\n(.+)", yt, flags=re.M)
    if m2:
        return re.sub(r"\s*#shorts\s*$", "", m2.group(1).strip(), flags=re.I)
    sh = load_json(os.path.join(d, "images", "shots.json"), {})
    if sh.get("title"):
        return sh["title"]
    cast = load_json(os.path.join(d, "images", "cast.json"), {})
    return cast.get("title") or re.sub(r"^(?:test-)?\d{3}-", "", os.path.basename(d)).replace("-", " ")


def state():
    out = []
    for c in channels():
        root = os.path.join(WS, c["videos"])
        os.makedirs(root, exist_ok=True)
        vids = []
        for slug in sorted(os.listdir(root), key=lambda x: (slug_num(x), x)):
            d = os.path.join(root, slug)
            if os.path.isdir(d) and SLUG_RE.match(slug):
                pub = bool(re.search(r"^Status: published", read(os.path.join(d, "VIDEO.md")), re.M))
                g = steps(d)
                cur = next((x for x in g["steps"] if x["key"] == g["next"]), None)
                vids.append({"slug": slug, "num": "%03d" % slug_num(slug), "title": title_of(d), "stages": stages(d),
                             "published": pub, "next": g["next"],
                             "next_label": cur["label"] if cur else "Xong", "next_who": cur["who"] if cur else "",
                             "done_steps": sum(x["done"] for x in g["steps"]), "total_steps": len(g["steps"]),
                             "render": (render_files(d, "%s/%s" % (c["id"], slug), dur=False) or [None])[0]})
        nums = [slug_num(v["slug"]) for v in vids]
        c = dict(c, next_num="%03d" % (max(nums + [0]) + 1))
        out.append(dict(c, list=vids))
    return {"channels": out, "jobs": job_list()}


def upload_sections(text):
    parts = re.split(r"^=== (.+?) ===\s*$", text, flags=re.M)
    secs = []
    for i in range(1, len(parts), 2):
        body = parts[i + 1].strip("\n")
        m = re.search(r"^-{20,}\n(.*?)\n-{20,}", body, flags=re.S | re.M)
        secs.append({"name": parts[i].strip(), "text": (m.group(1) if m else body).strip()})
    return secs


def youtube_txt_sections(text):
    if not text.strip():
        return []
    parts = re.split(r"^(TITLE \(chosen\)|TITLE \(alternatives\)|DESCRIPTION|TAGS|SETTINGS)\s*$", text.strip(), flags=re.M)
    secs = []
    for i in range(1, len(parts), 2):
        secs.append({"name": parts[i].strip(), "text": parts[i + 1].strip()})
    return secs


def read_upload_sections(d):
    up = read(os.path.join(d, "upload", "upload.txt"))
    if "=== " in up:
        return upload_sections(up)
    yt = read(os.path.join(d, "packaging", "youtube.txt"))
    return youtube_txt_sections(yt)


def render_files(d, tag, dur=True):
    """Finished MP4s in render/, newest first. Empty while a render job of this video runs (the file is still being written)."""
    rd = os.path.join(d, "render")
    if not os.path.isdir(rd) or any(j["kind"] == "render" and j["video"] == tag and j["status"] == "running" for j in JOBS.values()):
        return []
    fs = [os.path.join(rd, f) for f in os.listdir(rd) if f.endswith(".mp4")]
    return [{"path": rel(f), "name": os.path.basename(f), "mb": round(os.path.getsize(f) / 1e6, 1),
             "at": time.strftime("%d/%m %H:%M", time.localtime(os.path.getmtime(f))), "seconds": mp3_seconds(f) if dur else None}
            for f in sorted(fs, key=os.path.getmtime, reverse=True)]


def find_music_tracks(d):
    tracks, seen = [], set()
    for md in (os.path.join(d, "audio", "music"),
               os.path.join(os.path.dirname(d), "audio", "music"),
               os.path.join(os.path.dirname(d), "test-001-co-loa", "audio", "music")):
        if os.path.isdir(md):
            for f in sorted(os.listdir(md)):
                if f.endswith(".mp3") and f not in seen:
                    seen.add(f)
                    tracks.append({"name": f, "path": rel(os.path.join(md, f))})
    tracks.sort(key=lambda x: (0 if x["name"] == "zhuge_fuqin.mp3" else (1 if x["name"] == "Investigations.mp3" else 2), x["name"]))
    return tracks


def video_detail(cid, slug):
    d = video_dir(cid, slug)
    ch = channel(cid)
    shorts = is_shorts_ch(ch)
    img = os.path.join(d, "images")
    man = load_json(os.path.join(img, "prompts", "manifest.json"), {"items": []})
    st = load_json(os.path.join(img, "runs", "state.json"), {})
    items = []
    for it in man.get("items", []):
        s = st.get(it["id"], {})
        ref_links = []
        for r in it.get("refs", []):
            rp = os.path.abspath(os.path.join(img, r))
            if not os.path.exists(rp) and os.path.exists(os.path.join(WS, r)):
                rp = os.path.abspath(os.path.join(WS, r))
            ref_links.append({"label": os.path.basename(rp), "path": rel(rp) if rp.startswith(WS + os.sep) else r,
                              "exists": os.path.exists(rp)})
        clip_p = os.path.join(d, "clips", it["id"] + ".mp4")
        has_clip = os.path.exists(clip_p)
        items.append(dict(it, prompt=read(os.path.join(img, it["prompt_file"])), state=s.get("status", "pending"),
                          variants=[dict(v, path=rel(os.path.join(img, v["file"]))) for v in s.get("variants", [])],
                          chosen=s.get("chosen"), last_error=s.get("last_error", ""),
                          ref_links=ref_links,
                          clip=rel(clip_p) if has_clip else None,
                          clip_seconds=mp3_seconds(clip_p) if has_clip else None,
                          output=rel(os.path.join(img, it["save_as"])) if os.path.exists(os.path.join(img, it["save_as"])) else None))
    rv = load_json(os.path.join(img, "runs", "review.json"), {})
    clip_rv = load_json(os.path.join(img, "runs", "clip_review.json"), {})
    flow_st = load_json(os.path.join(img, "runs", "flow_state.json"), {})
    flow_q = load_json(os.path.join(img, "runs", "flow_decisions.json"), {})  # decisions a running Flow job has not taken yet
    flow_busy = {j["video"] for j in JOBS.values() if j["kind"] in ("flow_clips", "auto_video") and j["status"] == "running"}
    img_ok = load_json(os.path.join(img, "runs", "approvals.json"), {}).get("images", {})
    for it in items:
        fs = flow_st.get(it["id"])
        if fs:
            it["flow"] = dict(fs, file_path=rel(os.path.join(d, fs["file"])) if fs.get("file") and os.path.exists(os.path.join(d, fs["file"])) else None,
                              queued=flow_q.get(it["id"]), running=("%s/%s" % (cid, slug)) in flow_busy)
        ap = img_ok.get(it["id"])
        it["img_approved"] = bool(ap and it["output"] and abs(ap.get("mtime", 0) - os.path.getmtime(os.path.join(img, it["save_as"]))) < 1)
        r = rv.get(it["id"])
        if (r and it["output"] and r.get("file") == os.path.relpath(os.path.join(img, it["save_as"]), img)
                and abs(r.get("mtime", 0) - os.path.getmtime(os.path.join(img, it["save_as"]))) < 1):
            it["review"] = r
        clip_p = os.path.join(d, "clips", it["id"] + ".mp4")
        cr = clip_rv.get(it["id"])
        if cr and it["clip"] and os.path.exists(clip_p) and abs(cr.get("mtime", 0) - os.path.getmtime(clip_p)) < 1:
            cr_out = dict(cr)
            if cr.get("strip") and os.path.exists(os.path.join(d, cr["strip"])):
                cr_out["strip_path"] = rel(os.path.join(d, cr["strip"]))
            it["clip_review"] = cr_out
    render_rv = load_json(os.path.join(d, "render", "review.json"), None)
    if isinstance(render_rv, dict):
        render_rv = dict(render_rv)
        rf = os.path.join(d, render_rv.get("file", ""))
        render_rv["stale"] = (not os.path.exists(rf)) or (abs(render_rv.get("mtime", 0) - os.path.getmtime(rf)) >= 1)
        render_rv["grid_paths"] = [rel(os.path.join(d, g)) for g in render_rv.get("grids", []) if os.path.exists(os.path.join(d, g))]
    shots = {s["id"]: s for s in load_json(os.path.join(img, "shots.json"), {}).get("shots", [])}
    for it in items:
        if it["id"] in shots:
            it["vo"] = shots[it["id"]].get("vo", "")
            it["shot"] = shots[it["id"]]
    tts_dir = os.path.join(d, "script", "voiceover_tts")
    voice = []
    if os.path.isdir(tts_dir):
        for f in sorted(os.listdir(tts_dir)):
            if f.endswith(".txt") and (not shorts or re.match(r"^\d+$", f[:-4])):
                mp3 = os.path.join(d, "audio", f[:-4] + ".mp3")
                txt_val = read(os.path.join(tts_dir, f)).strip()
                voice.append({"n": f[:-4], "text": txt_val, "chars": len(txt_val),
                              "mp3": rel(mp3) if os.path.exists(mp3) else None,
                              "seconds": mp3_seconds(mp3) if os.path.exists(mp3) else None})
    sources = []
    sp = os.path.join(d, "research", "sources_log.csv")
    if os.path.exists(sp):
        sources = list(csv.DictReader(open(sp, encoding="utf-8")))
    renders = render_files(d, "%s/%s" % (cid, slug))
    refs = sorted(rel(os.path.join(img, "refs", f)) for f in os.listdir(os.path.join(img, "refs"))) if os.path.isdir(os.path.join(img, "refs")) else []
    thumbs = [rel(p) for p in (os.path.join(d, "upload", "thumbnail.png"),) if os.path.exists(p)]
    td = os.path.join(d, "upload", "thumbs")
    thumb_candidates = sorted(rel(os.path.join(td, f)) for f in os.listdir(td) if re.match(r"thumb_\d+\.png$", f)) if os.path.isdir(td) else []

    sid = style_id(d)
    style_obj = load_json(os.path.join(WS, "tools", "imageprompts", "style", sid.replace("-", "_") + ".json"), {})
    style_refs = [r for r in style_obj.get("style_refs", []) if os.path.exists(os.path.join(WS, r))]

    shorts_voice = None
    shorts_cover = None
    if shorts:
        pdir = os.path.join(d, "audio", "vbee_parts")
        p1_list = sorted(glob.glob(os.path.join(pdir, "part1.*"))) if os.path.isdir(pdir) else []
        p2_list = sorted(glob.glob(os.path.join(pdir, "part2.*"))) if os.path.isdir(pdir) else []
        p1 = p1_list[-1] if p1_list else None
        p2 = p2_list[-1] if p2_list else None
        vf = next((p for p in (os.path.join(d, "audio", n) for n in ("voice_full.wav", "voice_full.mp3")) if os.path.exists(p)), None)
        shorts_voice = {
            "part1_text": read(os.path.join(tts_dir, "part1.txt")).strip(),
            "part2_text": read(os.path.join(tts_dir, "part2.txt")).strip(),
            "full_text": read(os.path.join(tts_dir, "full.txt")).strip(),
            "part1_file": rel(p1) if p1 else None,
            "part1_seconds": mp3_seconds(p1) if p1 else None,
            "part2_file": rel(p2) if p2 else None,
            "part2_seconds": mp3_seconds(p2) if p2 else None,
            "voice_full": rel(vf) if vf else None,
            "voice_full_seconds": mp3_seconds(vf) if vf else None,
            "music_tracks": find_music_tracks(d),
        }
        cpy = read(os.path.join(d, "packaging", "cover.py"))
        cm = re.search(r'LINE1,\s*LINE2\s*=\s*"([^"]*)",\s*"([^"]*)"', cpy)
        cover_png = os.path.join(d, "packaging", "cover_1080x1920.png")
        cover_bg = os.path.join(d, "packaging", "cover_frame.png")
        shorts_cover = {
            "cover": rel(cover_png) if os.path.exists(cover_png) else None,
            "cover_bg": rel(cover_bg) if os.path.exists(cover_bg) else None,
            "line1": cm.group(1) if cm else "",
            "line2": cm.group(2) if cm else "",
        }

    return {"channel": cid, "slug": slug, "dir": rel(d), "title": title_of(d), "stages": stages(d), "guide": steps(d),
            "is_shorts": shorts, "gflow": flowcli.available(),
            "stats": gen_stats(d),
            "voice_cfg": dict(zip(("speed", "rate"), voice_cfg_of(d))),
            "auto": dict(workqueue.auto(d), image_queue=workqueue.peek(d, "image_queue.json", []),
                         decisions=workqueue.peek(d, "flow_decisions.json", {}),
                         running=sorted({j["kind"] for j in JOBS.values() if j["status"] == "running" and j.get("video") == "%s/%s" % (cid, slug)})), "aspect": ch.get("aspect", "16:9"), "language": ch.get("language", "en"),
            "has_custom_timeline": os.path.exists(os.path.join(d, "render", "timeline.py")) and not bool(items),
            "hook_reuse": man.get("hook_reuse"),
            "script": read(os.path.join(d, "script", "script.txt")), "sources": sources,
            "plan_md": read(os.path.join(d, "plan.md")),
            "cast": load_json(os.path.join(img, "cast.json")), "shots_json": read(os.path.join(img, "shots.json")),
            "cast_json": read(os.path.join(img, "cast.json")), "items": items, "refs": refs,
            "style_id": sid, "style": style_obj.get("style", ""), "style_note": style_obj.get("note", ""),
            "negative": style_obj.get("negative", ""), "style_refs": style_refs,
            "voice": voice, "shorts_voice": shorts_voice, "shorts_cover": shorts_cover,
            "youtube_txt": read(os.path.join(d, "packaging", "youtube.txt")),
            "renders": renders, "render_review": render_rv, "thumbs": thumbs, "thumb_candidates": thumb_candidates,
            "sim": [{"file": f, "text": read(os.path.join(d, "research", "gemini", f))} for f in gfiles(d, "simulate")][-1:],
            "upload": read_upload_sections(d),
            "claude_history": [json.loads(l) for l in read(os.path.join(d, ".dashboard", "claude.jsonl")).splitlines() if l.strip()][-30:]}


# ---------------------------------------------------------------- jobs
def job_list():
    with LOCK:
        return sorted(({k: v for k, v in j.items() if k != "proc"} for j in JOBS.values()), key=lambda j: -j["started"])[:30]


KEEP_AWAKE = {"auto_video", "flow_clips", "auto_images", "generate"}  # Flow needs a visible, awake Chrome


# what a runner is doing right now, read from its log lines; shown as the job's label in the dashboard
PROGRESS = {
    "flow_clips": [(re.compile(r"^\[(\S+)\] (lite|fast) with"), "Flow: tạo clip {0} ({1})"),
                   (re.compile(r"^\[(\S+)\] upscale 1080p"), "Flow: nâng 1080p {0}"),
                   (re.compile(r"^\[(\S+)\] \S+: fetching the paid clip"), "Flow: tải lại clip đã trả tiền {0}"),
                   (re.compile(r"^fetching already-paid clip"), "Flow: tải lại clip đã trả tiền"),
                   (re.compile(r"^Đang trích xuất dải 6 frame"), "Gemini kiểm clip"),
                   (re.compile(r"^(\S+): new motion prompt"), "Gemini viết lại prompt {0}"),
                   (re.compile(r"^pause (\d+) s before"), "Flow: nghỉ {0}s trước lần gọi tiếp"),
                   (re.compile(r"^Gemini reviews (\d+) start image"), "Gemini kiểm {0} ảnh khung đầu"),
                   (re.compile(r"^lessons:"), "Gemini rút bài học từ góp ý"),
                   (re.compile(r"^Paused by the owner"), "Đã tạm dừng")],
    "auto_images": [(re.compile(r"^preflight: Gemini checks (\d+)"), "Gemini soát {0} prompt trước khi tạo"),
                    (re.compile(r"^== round (\d+): generate"), "Tạo ảnh (vòng {0})"),
                    (re.compile(r"^== round (\d+): Gemini review"), "Gemini kiểm ảnh (vòng {0})"),
                    (re.compile(r"^redo automatically"), "Tự làm lại ảnh 1–2 điểm"),
                    (re.compile(r"^pause (\d+) s before"), "Flow: nghỉ {0}s trước lần gọi tiếp"),
                    (re.compile(r"^lessons:"), "Gemini rút bài học từ góp ý")],
}


def start_job(kind, cmd, label, video=None, cwd=WS, on_line=None, on_end=None):
    if kind in KEEP_AWAKE and shutil.which("caffeinate"):
        cmd = ["caffeinate", "-d", "-i"] + list(cmd)  # no idle sleep, no display sleep (so no auto-lock) while it runs
    jid = uuid.uuid4().hex[:10]
    log = os.path.join(JOBS_DIR, jid + ".log")
    job = {"id": jid, "kind": kind, "label": label, "video": video, "cmd": " ".join(cmd)[:300], "status": "running",
           "started": time.time(), "ended": None, "code": None, "log": rel(log)}
    if kind in PROGRESS and on_line is None:
        def on_line(line, _rules=PROGRESS[kind]):
            for rx, text in _rules:
                m = rx.search(line.strip())
                if m:
                    job["label"] = text.format(*m.groups())
                    break
            return line
    if kind in ("auto_images", "flow_clips") and video:
        try:
            job["vdir"] = video_dir(*video.split("/", 1))
            job["sig"] = signature(job["vdir"], kind)
        except (KeyError, ValueError):
            pass

    def worker():
        with open(log, "w", encoding="utf-8") as fh:
            fh.write("$ %s\n" % " ".join(cmd)[:2000])
            fh.flush()
            try:
                p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                                     start_new_session=True)  # own process group: "Dừng" also stops caffeinate's child
            except OSError as e:
                fh.write("could not start: %s\n" % e)
                job.update(status="failed", ended=time.time(), code=-1)
                return
            job["proc"] = p
            for line in p.stdout:
                fh.write(on_line(line) if on_line else line)
                fh.flush()
            p.wait()
            job.update(status="done" if p.returncode == 0 else ("stopped" if job.get("stop") else "failed"),
                       ended=time.time(), code=p.returncode)
            if on_end:
                on_end(job)
            try:
                runner_ended(job)
            except Exception as e:  # noqa: BLE001
                print("runner_ended: %s" % e, flush=True)
            if kind == "render" and job["status"] == "done" and video:  # owner: open the finished video right away
                try:
                    rd = os.path.join(video_dir(*video.split("/", 1)), "render")
                    vids = [os.path.join(rd, f) for f in os.listdir(rd) if f.endswith(".mp4") and os.path.getmtime(os.path.join(rd, f)) >= job["started"]]
                    music = [v for v in vids if "youtube" in os.path.basename(v) or "music" in os.path.basename(v)]
                    if vids:
                        subprocess.Popen(["open", (music or sorted(vids, key=os.path.getmtime))[-1]])
                except (KeyError, ValueError, OSError) as e:
                    print("open render: %s" % e, flush=True)
            # Telegram: failures, and long jobs finishing (auto_images / flow_clips send their own summaries)
            if kind not in ("auto_images", "flow_clips") and (job["status"] == "failed" or kind in NOTIFY_DONE):
                notify.send("%s %s: %s (%d phút)%s" % ("✅" if job["status"] == "done" else "❌", video or "Studio", label,
                                                       round((job["ended"] - job["started"]) / 60),
                                                       "\n" + notify.video_link(os.path.join(WS, "channels", video), "") if video else ""))
    with LOCK:
        JOBS[jid] = job
    threading.Thread(target=worker, daemon=True).start()
    return job


def stop_job(jid):
    j = JOBS.get(jid)
    if j and j.get("proc") and j["status"] == "running":
        j["stop"] = True
        try:
            os.killpg(os.getpgid(j["proc"].pid), signal.SIGTERM)
        except (OSError, ProcessLookupError):
            j["proc"].terminate()


# ---------------------------------------------------------------- actions
PY = sys.executable


# ---------------------------------------------------------------- work queue + reconciler
# Owner actions only write to the per-video queue (tools/workqueue.py) and switch automation on; reconcile()
# starts whatever runner is missing. It also runs every 30 s, so work left over after a crash, a dashboard
# restart or a request that arrived as a run ended is always picked up. Pause = finish the step in progress.
def voice_cfg_of(d):
    sys.path.insert(0, os.path.join(WS, "tools", "shorts"))
    from voice_shorts import voice_cfg
    return voice_cfg(d)


def gen_stats(d):
    """How many tries images and clips need: the number to push down with prompt lessons and pre-flight checks."""
    img = os.path.join(d, "images")
    man = [i for i in load_json(os.path.join(img, "prompts", "manifest.json"), {"items": []})["items"] if i["kind"] == "scene"]
    st = load_json(os.path.join(img, "runs", "state.json"), {})
    rv = load_json(os.path.join(img, "runs", "review.json"), {})
    ok = load_json(os.path.join(img, "runs", "approvals.json"), {}).get("images", {})
    made = {i["id"]: len(st.get(i["id"], {}).get("variants", [])) for i in man}
    made = {k: v for k, v in made.items() if v}
    first = sum(1 for k, v in made.items() if v == 1 and (rv.get(k, {}).get("score", 0) >= PASS or k in ok))
    fl = load_json(os.path.join(img, "runs", "flow_state.json"), {})
    done = [s for s in fl.values() if s.get("stage") == "done"]
    gens = sum(sum(s.get("tries", {}).values()) for s in fl.values())
    return {"images": len(made), "image_tries": sum(made.values()), "image_first": first,
            "clips_done": len(done), "clip_gens": gens,
            "clip_first": sum(1 for s in done if all(v == 1 for v in s.get("tries", {}).values())),
            "lessons": len(load_json(os.path.join(channel_root(d), "prompt_lessons.json"), {}).get("lessons", []))}


def channel_root(d):
    parts = os.path.relpath(d, os.path.join(WS, "channels")).split(os.sep)
    return os.path.join(WS, "channels", parts[0])


def tag_of(d):
    parts = os.path.relpath(d, os.path.join(WS, "channels")).split(os.sep)
    return "%s/%s" % (parts[0], parts[-1])


def _mt(p):
    try:
        return os.path.getmtime(p)
    except OSError:
        return 0


def signature(d, kind):
    """What a runner of this kind reads; if a run ends without changing anything, it is not restarted
    until one of these changes (stops a no-op restart loop)."""
    r = os.path.join(d, "images", "runs")
    names = {"flow_clips": ("flow_state.json", "review.json", "approvals.json", "flow_decisions.json", "../shots.json"),
             "auto_images": ("state.json", "review.json", "image_queue.json", "approvals.json", "../prompts/manifest.json")}[kind]
    return [round(_mt(os.path.join(r, n)), 3) for n in names] + [round(_mt(os.path.join(d, "images", "frames")), 3)]


def images_pending(d):
    img = os.path.join(d, "images")
    if workqueue.peek(d, "image_queue.json", []):
        return True
    rv = load_json(os.path.join(img, "runs", "review.json"), {})
    for i in load_json(os.path.join(img, "prompts", "manifest.json"), {"items": []})["items"]:
        if i["kind"] != "scene" or (i.get("route") == "manual" and not flowcli.available()):
            continue
        p = os.path.join(img, i["save_as"])
        if not os.path.exists(p) or abs(rv.get(i["id"], {}).get("mtime", 0) - os.path.getmtime(p)) >= 1:
            return True
    return False


def clips_pending(d):
    if workqueue.peek(d, "flow_decisions.json", {}):
        return True
    img = os.path.join(d, "images")
    rv = load_json(os.path.join(img, "runs", "review.json"), {})
    ok = load_json(os.path.join(img, "runs", "approvals.json"), {}).get("images", {})
    st = load_json(os.path.join(img, "runs", "flow_state.json"), {})
    shots = {s["id"]: s for s in load_json(os.path.join(img, "shots.json"), {}).get("shots", [])}
    for i in load_json(os.path.join(img, "prompts", "manifest.json"), {"items": []})["items"]:
        f = st.get(i["id"], {})
        if i["kind"] != "scene" or not (shots.get(i["id"], {}).get("veo_prompt") or shots.get(i["id"], {}).get("motion")):
            continue
        if f.get("stage") == "done" or f.get("status") == "ask":
            continue
        if f.get("stage") not in (None, "lite"):
            return True  # mid-way (fast or upscale): needs no new image check
        p = os.path.join(img, i["save_as"])
        if os.path.exists(p):
            m = os.path.getmtime(p)
            if abs(ok.get(i["id"], {}).get("mtime", 0) - m) < 1 or (
                    rv.get(i["id"], {}).get("score", 0) >= PASS and abs(rv[i["id"]].get("mtime", 0) - m) < 1):
                return True
    return False


RECONCILE_LOCK = threading.Lock()


def reconcile(d):
    """Start the image and/or clip runner a video needs, unless automation is off or paused."""
    with RECONCILE_LOCK:
        a = workqueue.auto(d)
        if not a.get("enabled") or a.get("pause") or time.time() < a.get("cooldown_until", 0):
            return []
        tag, started = tag_of(d), []
        # clips a run still holds for the owner although they now pass (threshold lowered while it ran): approve
        q = workqueue.peek(d, "flow_decisions.json", {})
        for sid, f in load_json(os.path.join(d, "images", "runs", "flow_state.json"), {}).items():
            if f.get("status") == "ask" and (f.get("score") or 0) >= PASS and sid not in q:
                workqueue.add_decision(d, sid, True)
        running = {j["kind"] for j in JOBS.values() if j["status"] == "running" and j.get("video") == tag}
        noop = a.get("noop", {})
        if ("auto_images" not in running and not workqueue.busy(d, "auto_images.lock") and images_pending(d)
                and noop.get("auto_images") != signature(d, "auto_images")):
            started.append(start_job("auto_images", [PY, "-u", "tools/gemini/auto_images.py", d, "--workers",
                                                     str(CFG["gemini"].get("workers", 3))], "Tạo + kiểm + tự sửa ảnh", tag))
        if (is_shorts(d) and "flow_clips" not in running and not workqueue.busy(d, "flow_clips.lock") and clips_pending(d)
                and noop.get("flow_clips") != signature(d, "flow_clips")):
            started.append(start_job("flow_clips", [PY, "-u", "tools/shorts/flow_clips.py", d], "Flow tạo clip Veo", tag))
        return started


def reconciler():
    while True:
        time.sleep(30)
        for p in glob.glob(os.path.join(WS, "channels", "**", "images", "runs", "auto.json"), recursive=True):
            d = os.path.dirname(os.path.dirname(os.path.dirname(p)))
            try:
                reconcile(d)
            except Exception as e:  # noqa: BLE001  one broken video must not stop the others
                print("reconcile %s: %s" % (d, e), flush=True)


def runner_ended(job):
    """After an image or clip run: pause automation on a failure or a manual stop, mark no-op runs, go on."""
    if job["kind"] not in ("auto_images", "flow_clips") or not job.get("video") or not job.get("vdir"):
        return
    d = job["vdir"]
    if job["status"] == "stopped":
        workqueue.set_auto(d, pause=True, reason="Bạn đã bấm Dừng")
    elif job["status"] == "failed":
        a = workqueue.auto(d)
        err = a.get("last_error") or {}
        recent = err.get("at", "") >= time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(job["started"]))
        kind = err.get("kind") if (job["kind"] == "flow_clips" and recent) else "hard"
        streak = a.get("fail_streak", 0) + 1
        if kind in ("transient", "waf") and streak <= 3:  # retry by itself after a cool-down
            wait = 35 * 60 if kind == "waf" else 180
            workqueue.set_auto(d, fail_streak=streak, cooldown_until=time.time() + wait,
                               reason="Tự thử lại lúc %s (%s)" % (time.strftime("%H:%M", time.localtime(time.time() + wait)), err.get("text", "")))
        else:
            workqueue.set_auto(d, pause=True, fail_streak=streak,
                               reason="%s dừng vì lỗi%s. Bấm Tiếp tục khi đã xử lý." % (
                                   "Flow" if job["kind"] == "flow_clips" else "Tạo ảnh",
                                   (": " + err["text"]) if recent and err.get("text") else " (xem log / Telegram)"))
    else:
        if job["kind"] == "flow_clips":
            workqueue.set_auto(d, fail_streak=0)
        now, before = signature(d, job["kind"]), job.get("sig")
        noop = workqueue.auto(d).get("noop", {})
        noop[job["kind"]] = now if now == before else None
        workqueue.set_auto(d, noop=noop)
        reconcile(d)


def act(body):
    a = body.get("action")
    cid, slug = body.get("channel"), body.get("slug")
    d = video_dir(cid, slug) if slug else None
    tag = "%s/%s" % (cid, slug) if slug else None
    shorts = is_shorts(d) if d else (is_shorts_ch(channel(cid)) if cid else False)
    prompt_tool = "tools/shorts/make_shorts_prompts.py" if shorts else "tools/imageprompts/make_prompts.py"
    if d and a in ("prompts", "generate", "auto_images") and not body.get("only"):
        au = workqueue.auto(d)
        if (au.get("enabled") and not au.get("pause")) or any(
                j["video"] == tag and j["kind"] in ("auto_images", "flow_clips", "auto_video") and j["status"] == "running" for j in JOBS.values()):
            return {"ok": False, "out": "Tự động đang chạy: bấm ⏸ Tạm dừng và chờ bước đang làm xong trước."}
    if a == "prompts":
        return start_job(a, [PY, prompt_tool, d], "Tạo prompt 9:16 + Veo" if shorts else "Tạo prompt ảnh", tag)
    if a == "check_prompts":
        return start_job(a, [PY, prompt_tool, d, "--check"], "Kiểm prompt", tag)
    if a == "generate":
        cmd = [PY, "-u", "tools/gemini/agy_images.py", d, "--workers", str(int(body.get("workers") or CFG["gemini"].get("workers", 3)))]
        if body.get("only"):
            cmd += ["--only", ",".join(body["only"])]
        if body.get("limit"):
            cmd += ["--limit", str(int(body["limit"]))]
        return start_job(a, cmd, "Tạo ảnh bằng Gemini" + (" (%s)" % ",".join(body["only"]) if body.get("only") else ""), tag)
    if a in ("redo_many", "redo"):  # owner's redo: queued, then made again with the review's fix, reviewed, rule applied
        ids = [i for i in (body.get("ids") or [body.get("id", "")]) if re.match(r"^[\w-]+$", i)]
        if not ids:
            return {"ok": False, "out": "Thiếu id ảnh"}
        workqueue.add_images(d, ids)
        if not workqueue.auto(d).get("enabled"):
            workqueue.set_auto(d, enabled=True)
        reconcile(d)
        return {"ok": True, "out": "Đã xếp %s vào hàng đợi làm lại ảnh." % ",".join(ids)}
    if a == "approve":
        cmd = [PY, "tools/gemini/agy_images.py", d, "--approve", body["id"]]
        if body.get("variant"):
            cmd += ["--variant", str(int(body["variant"]))]
        p = subprocess.run(cmd, cwd=WS, capture_output=True, text=True)
        return {"ok": p.returncode == 0, "out": p.stdout + p.stderr}
    if a == "compose":  # the cast sheet is pasted together from the approved model sheets, never generated
        p = subprocess.run([PY, "tools/gemini/agy_images.py", d, "--compose"], cwd=WS, capture_output=True, text=True)
        return {"ok": p.returncode == 0, "out": p.stdout + p.stderr}
    if a == "review":
        cmd = [PY, "-u", "tools/gemini/agy_review.py", d, "--workers", "3"] + (["--only", ",".join(body["only"])] if body.get("only") else [])
        if body.get("all"):
            cmd.append("--all")
        return start_job(a, cmd, "Gemini kiểm ảnh" + (" (%s)" % ",".join(body["only"]) if body.get("only") else ""), tag)
    if a == "review_clips":
        cmd = [PY, "-u", "tools/shorts/review_video.py", d, "--clips"] + (["--only", ",".join(body["only"])] if body.get("only") else [])
        if body.get("all"):
            cmd.append("--all")
        return start_job(a, cmd, "Gemini kiểm clip Veo" + (" (%s)" % ",".join(body["only"]) if body.get("only") else ""), tag)
    if a in ("auto_video", "auto_resume"):  # the one button / Tiếp tục: automation on, then start what is missing
        workqueue.set_auto(d, enabled=True, pause=False, reason="", noop={}, cooldown_until=0, fail_streak=0)
        started = reconcile(d)
        return {"ok": True, "out": "Tự động đang chạy: " + (", ".join(j["label"] for j in started) if started else
                                                           "không còn việc nào ngay lúc này; sẽ tự nhận việc mới.")}
    if a == "auto_pause":  # finish the step in progress, start nothing new
        workqueue.set_auto(d, pause=True, reason="Bạn đã bấm Tạm dừng")
        return {"ok": True, "out": "Sẽ dừng sau khi xong bước đang làm (ảnh/clip đang tạo vẫn hoàn tất)."}
    if a == "auto_images":  # generate -> Gemini review -> redo 1-2/5 by itself; 3-4/5 wait for the owner
        cmd = [PY, "-u", "tools/gemini/auto_images.py", d, "--workers", str(int(body.get("workers") or CFG["gemini"].get("workers", 3)))]
        return start_job(a, cmd, "Tạo + kiểm + tự sửa ảnh", tag)
    if a == "approve_image":  # owner keeps an image Gemini scored below 5 (valid for this exact file only)
        iid = body.get("id", "")
        it = next((i for i in load_json(os.path.join(d, "images", "prompts", "manifest.json"), {"items": []})["items"] if i["id"] == iid), None)
        p = os.path.join(d, "images", it["save_as"]) if it else ""
        if not it or not os.path.exists(p):
            return {"ok": False, "out": "Không tìm thấy ảnh %s" % iid}
        ap_p = os.path.join(d, "images", "runs", "approvals.json")
        ap = load_json(ap_p, {})
        ap.setdefault("images", {})[iid] = {"mtime": os.path.getmtime(p), "at": time.strftime("%Y-%m-%d %H:%M")}
        json.dump(ap, open(ap_p, "w", encoding="utf-8"), indent=1)
        if not workqueue.auto(d).get("enabled"):
            workqueue.set_auto(d, enabled=True)
        reconcile(d)
        return {"ok": True, "out": "Đã duyệt ảnh %s; cảnh này vào hàng đợi tạo clip." % iid}
    if a == "flow_reset":  # owner remakes a finished clip from veo-lite; the current clip stays until the new one passes
        sid = body.get("id", "")
        if not re.match(r"^[\w-]+$", sid):
            return {"ok": False, "out": "Thiếu id cảnh"}
        workqueue.add_decision(d, sid, False, value="reset")  # applied by the Flow run (never two writers on its state)
        workqueue.set_auto(d, enabled=True, pause=False, reason="", cooldown_until=0, fail_streak=0)
        started = reconcile(d)
        return {"ok": True, "out": "Đang tạo lại clip %s từ veo-lite%s." % (sid, "" if started else "; lượt Flow đang chạy sẽ nhận")}
    if a in ("flow_clips", "flow_decide"):  # clip decisions and "make clips" only feed the queue
        if a == "flow_decide":
            if not re.match(r"^[\w-]+$", body.get("id", "")):
                return {"ok": False, "out": "Thiếu id cảnh"}
            workqueue.add_decision(d, body["id"], bool(body.get("approve")))
        if not workqueue.auto(d).get("enabled"):
            workqueue.set_auto(d, enabled=True)
        started = reconcile(d)
        msg = "Đã ghi vào hàng đợi." + ("" if started else " Lượt đang chạy sẽ xử lý" + (" (đang Tạm dừng: bấm Tiếp tục)." if workqueue.pause_requested(d) else "."))
        return started[0] if started else {"ok": True, "out": msg}
    if a == "review_render":
        cmd = [PY, "-u", "tools/shorts/review_video.py", d, "--render"] + (["--file", body["path"]] if body.get("path") else [])
        return start_job(a, cmd, "Gemini kiểm bản dựng 9:16", tag)
    if a == "thumb":
        return start_job(a, [PY, "-u", "tools/gemini/agy_thumb.py", d, body["concept"], body.get("text", "")], "Gemini tạo thumbnail", tag)
    if a == "use_thumb":
        src = safe(body["path"])
        if not src or not src.startswith(d + os.sep):
            raise KeyError("bad thumbnail path")
        shutil.copy2(src, os.path.join(d, "upload", "thumbnail.png"))
        return {"ok": True, "out": "Đã chọn thumbnail"}
    if a == "make_cover":
        l1 = (body.get("line1") or "").strip()
        l2 = (body.get("line2") or "").strip()
        cpy = os.path.join(d, "packaging", "cover.py")
        if (l1 or l2) and os.path.exists(cpy):
            txt = read(cpy)
            txt = re.sub(r'LINE1,\s*LINE2\s*=\s*"[^"]*",\s*"[^"]*"',
                         'LINE1, LINE2 = %s, %s' % (json.dumps(l1, ensure_ascii=False), json.dumps(l2, ensure_ascii=False)), txt)
            open(cpy, "w", encoding="utf-8").write(txt)
        cmd = [PY, "-u", "tools/shorts/make_cover.py", d]
        if l1:
            cmd += ["--line1", l1]
        if l2:
            cmd += ["--line2", l2]
        if body.get("bg"):
            cmd += ["--bg", body["bg"]]
        return start_job(a, cmd, "Tạo ảnh bìa 1080x1920", tag)
    if a in PRESETS:
        return gemini_job(PRESETS[a](d, body), d, tag, cid, name=a, query=(body.get("query") or "").strip(),
                          label=PRESET_LABELS[a] + (": " + body["query"].strip()[:50] if body.get("query") else ""))
    if a in CLAUDE_TASKS:
        return claude_job(CLAUDE_TASKS[a][1](d), d, tag, cid, body.get("model"), body.get("effort"), label=CLAUDE_TASKS[a][0])
    if a == "delete_script":
        # keep a copy (research/script_versions/) and reset the script, voice text and sources to the empty template
        stamp = time.strftime("%Y%m%d_%H%M%S")
        keep = os.path.join(d, "research", "script_versions")
        os.makedirs(keep, exist_ok=True)
        for src, name in ((os.path.join(d, "script", "script.txt"), "script_%s.txt"),
                          (os.path.join(d, "research", "sources_log.csv"), "sources_log_%s.csv")):
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(keep, name % stamp))
        os.makedirs(os.path.join(d, "script"), exist_ok=True)
        shutil.copy2(os.path.join(WS, "templates", "video", "script", "script.txt"), os.path.join(d, "script", "script.txt"))
        shutil.copy2(os.path.join(WS, "templates", "video", "research", "sources_log.csv"), os.path.join(d, "research", "sources_log.csv"))
        tts = os.path.join(d, "script", "voiceover_tts")
        if os.path.isdir(tts):
            for f in os.listdir(tts):
                if f.endswith(".txt"):
                    os.remove(os.path.join(tts, f))
        return {"ok": True, "out": "Đã xóa kịch bản. Bản cũ lưu ở research/script_versions/script_%s.txt" % stamp}
    if a == "confirm":  # an image file is already in place (e.g. copied by hand): record it as accepted
        img = os.path.join(d, "images")
        man = {i["id"]: i for i in load_json(os.path.join(img, "prompts", "manifest.json"), {}).get("items", [])}
        it = man[body["id"]]
        stp = os.path.join(img, "runs", "state.json")
        if not os.path.exists(os.path.join(img, it["save_as"])):
            return {"ok": False, "out": "chưa có file ảnh"}
        os.makedirs(os.path.dirname(stp), exist_ok=True)
        with open(stp + ".lock", "w") as lf:  # same lock as agy_images.py: image jobs may be saving at the same time
            fcntl.flock(lf, fcntl.LOCK_EX)
            st = load_json(stp, {})
            e = st.setdefault(it["id"], {"variants": [], "attempts": 0})
            e["variants"] = e.get("variants") or [{"file": it["save_as"], "source": "existing file", "conversation": "manual", "problems": []}]
            e["chosen"] = len(e["variants"])
            e["status"] = "approved" if it["kind"] != "scene" else "done"
            json.dump(st, open(stp + ".tmp", "w"), indent=1)
            os.replace(stp + ".tmp", stp)
        if it["kind"] == "model_sheet":  # same as approving through agy_images.py: rebuild the cast sheet
            subprocess.run([PY, "tools/gemini/agy_images.py", d, "--compose"], cwd=WS, capture_output=True)
        return {"ok": True, "out": "Đã xác nhận ảnh %s" % it["id"]}
    if a == "open_tts":  # Finder on the folder the Edge extension picks .txt files from
        subprocess.run(["open", os.path.join(d, "script", "voiceover_tts")])
        return {"ok": True, "out": "Đã mở thư mục text giọng trong Finder"}
    if a == "import_tts":
        # the Edge extension saves NN.mp3 into ~/Downloads/tts/; take only files newer than this video's voice text
        src = os.path.expanduser("~/Downloads/tts")
        tts = os.path.join(d, "script", "voiceover_tts")
        need = sorted(f[:-4] for f in os.listdir(tts) if f.endswith(".txt")) if os.path.isdir(tts) else []
        since = min(os.path.getmtime(os.path.join(tts, n + ".txt")) for n in need) if need else 0
        got, old, missing = [], [], []
        for n in need:
            f = os.path.join(src, n + ".mp3")
            if not os.path.exists(f):
                missing.append(n)
            elif os.path.getmtime(f) < since:
                old.append(n)
            elif body.get("apply"):
                os.makedirs(os.path.join(d, "audio"), exist_ok=True)
                shutil.copy2(f, os.path.join(d, "audio", n + ".mp3"))
                got.append(n)
            else:
                got.append(n)
        verb = "Đã chép" if body.get("apply") else "Sẽ chép"
        out = "%s %d file: %s" % (verb, len(got), ", ".join(got) or "không có")
        if old:
            out += ". Bỏ qua %d file cũ hơn text giọng (có thể của video khác): %s" % (len(old), ", ".join(old))
        if missing:
            out += ". Chưa có: %s" % ", ".join(missing)
        return {"ok": True, "out": out, "got": got, "old": old, "missing": missing}
    if a == "save_shot":  # owner edited one shot: write it back to shots.json and rebuild the prompts (others stay identical)
        sp = os.path.join(d, "images", "shots.json")
        data = load_json(sp, {})
        new = body["shot"] if isinstance(body["shot"], dict) else json.loads(body["shot"])
        if new.get("id") != body["id"]:
            return {"ok": False, "out": "id của cảnh không được đổi"}
        idx = next((k for k, x in enumerate(data.get("shots", [])) if x["id"] == body["id"]), None)
        if idx is None:
            return {"ok": False, "out": "không thấy cảnh " + body["id"]}
        old = data["shots"][idx]
        data["shots"][idx] = new
        tmp = sp + ".tmp"
        json.dump(data, open(tmp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        os.replace(tmp, sp)
        p = subprocess.run([PY, prompt_tool, d], cwd=WS, capture_output=True, text=True)
        if p.returncode != 0:  # broken edit: put the old shot back so the video keeps working
            data["shots"][idx] = old
            json.dump(data, open(sp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            subprocess.run([PY, prompt_tool, d], cwd=WS, capture_output=True)
            return {"ok": False, "out": "Không lưu, prompt không hợp lệ:\n" + (p.stdout + p.stderr)[-800:]}
        return {"ok": True, "out": "Đã tạo lại prompt cho " + body["id"]}
    if a == "claude_shot":  # Claude rewrites one shot from the owner's note
        if shorts:
            prompt_msg = (
                "In %s, rewrite ONLY shot \"%s\" in images/shots.json according to the owner's note. "
                "Keep id, block, duration, xfade and [STYLE LOCK] (tools/imageprompts/style/vn_ligne_claire.json: 2D hand-drawn ink & muted watercolor, "
                "6-head human proportions, vertical 9:16, no text/UI). Update both \"prompt\" (9:16 image) and \"veo_prompt\" (single subtle motion, "
                "no voices/music) if needed. Owner's note: %s\nThen run python3 tools/shorts/make_shorts_prompts.py %s until 0 errors, and reply in Vietnamese."
                % (d, body["id"], body.get("note", ""), d)
            )
        else:
            prompt_msg = (
                "In %s, rewrite ONLY the shot \"%s\" in images/shots.json (and add a pose or location to images/cast.json only if this shot "
                "needs a new one). The owner's note follows; it may describe a DEFECT seen in the current image (for example a review "
                "finding like 'has thick white limbs') or a CHANGE they want. If it describes a defect, rewrite the shot so the next image "
                "avoids that defect; never write the defect into the prompt. The result must obey the image style named in images/cast.json "
                "(its STYLE block in tools/imageprompts/style/) and the character cards (body, clothing, one-sided items on the stated side); "
                "never ask for anything that breaks them. "
                "Owner's note: %s\nKeep its id, block and sentence. Then run python3 tools/imageprompts/make_prompts.py %s until "
                "it reports 0 errors, and reply in Vietnamese with the new scene text and how you read the note." % (d, body["id"], body.get("note", ""), d)
            )
        return claude_job(prompt_msg, d, tag, cid, body.get("model"), body.get("effort"), label="viết lại prompt " + body["id"])
    if a == "voice_text":
        vtool = "tools/shorts/voice_shorts.py" if shorts else "tools/pipeline/voice_text.py"
        return start_job(a, [PY, vtool, d], "Tách text giọng (Part 1 & Part 2 < 60s)" if shorts else "Tạo text giọng đọc", tag)
    if a == "join_voice":
        return start_job(a, [PY, "-u", "tools/shorts/voice_shorts.py", d, "--join"], "Ghép Part 1 + Part 2 → voice_full.wav", tag)
    if a == "render":
        if shorts:
            cmd = [PY, "-u", "tools/shorts/render_shorts.py", d]
            if body.get("music"):
                cmd += ["--music", body["music"]]
            if body.get("smooth"):
                cmd.append("--smooth")
            return start_job(a, cmd, "Dựng video 9:16 (TikTok 1080p + YouTube 4K)" + (" · khử giật Veo" if body.get("smooth") else ""), tag)
        if os.path.exists(os.path.join(d, "images", "prompts", "manifest.json")):
            cmd = ["tools/anim/render_frames.sh", d]
        else:
            cmd = ["tools/anim/render.sh", d]
        return start_job(a, cmd, "Dựng video 1440p", tag)
    if a == "open_render":  # MP4s in render/ or clips/, or (Finder only) upload/thumbnail or packaging/cover*
        f = os.path.realpath(os.path.join(WS, body.get("path", "")))
        mp4 = (f.startswith(os.path.realpath(os.path.join(d, "render")) + os.sep)
               or f.startswith(os.path.realpath(os.path.join(d, "clips")) + os.sep)) and f.endswith(".mp4")
        thumb = body.get("finder") and (
            (os.path.dirname(f) == os.path.realpath(os.path.join(d, "upload")) and re.match(r"^thumbnail\.(png|jpg)$", os.path.basename(f)))
            or (os.path.dirname(f) == os.path.realpath(os.path.join(d, "packaging")) and re.match(r"^cover.*\.(png|jpg)$", os.path.basename(f)))
        )
        if not ((mp4 or thumb) and os.path.exists(f)):
            return {"ok": False, "out": "không tìm thấy file"}
        subprocess.run(["open", "-R", f] if body.get("finder") else ["open", "-a", "QuickTime Player", f])
        return {"ok": True, "out": "Đã mở " + os.path.basename(f)}
    if a == "studio":
        return start_job(a, ["tools/anim/render.sh", d, "studio"], "Remotion Studio", tag)
    if a == "new_video":
        c = channel(cid)
        root = os.path.join(WS, c["videos"])
        os.makedirs(root, exist_ok=True)
        num = (body.get("num") or "").strip()
        if not num:  # next free number in this channel
            used = [slug_num(x) for x in os.listdir(root) if SLUG_RE.match(x)]
            num = "%03d" % (max(used + [0]) + 1)
        raw_name = ascii_slug(body.get("name") or body.get("topic") or "")
        words = re.findall(r"[a-z0-9]+", raw_name)
        stop = ("how", "did", "the", "a", "an", "of", "in", "to", "what", "do", "does", "cach", "xay", "lam", "the", "nao", "nhu")
        s = "-".join(w for w in words if w not in stop)[:40].strip("-") or "-".join(words)[:40].strip("-") or "new-video"
        nd = os.path.join(root, "%s-%s" % (num, s))
        if not re.match(r"^\d{3}$", num) or os.path.exists(nd):
            return {"ok": False, "out": "số video sai hoặc đã có"}
        shutil.copytree(os.path.join(WS, "templates", "video"), nd)
        md = os.path.join(nd, "VIDEO.md")
        open(md, "w").write(read(md).replace("{{ID}}", num).replace("{{SLUG}}", s))
        if is_shorts_ch(c):
            os.makedirs(os.path.join(nd, "clips"), exist_ok=True)
            os.makedirs(os.path.join(nd, "packaging"), exist_ok=True)
            os.makedirs(os.path.join(nd, "images"), exist_ok=True)
            t_title = (body.get("name") or body.get("topic") or s.replace("-", " ")).strip()
            json.dump({"title": t_title, "style": c.get("style", "vn-ligne-claire"), "aspect": "9:16", "shots": []},
                      open(os.path.join(nd, "images", "shots.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        if body.get("topic"):  # started from a measured search phrase: keep the evidence with the video
            gdir = os.path.join(research_dir(cid), "gemini")
            for f in sorted(os.listdir(gdir)) if os.path.isdir(gdir) else []:
                if f.endswith(".md") and ("<!-- query: %s -->" % body["topic"].strip()) in read(os.path.join(gdir, f))[:300]:
                    os.makedirs(os.path.join(nd, "research", "gemini"), exist_ok=True)
                    shutil.copy2(os.path.join(gdir, f), os.path.join(nd, "research", "gemini", f))
            open(os.path.join(nd, "research", "topic.md"), "w", encoding="utf-8").write(
                "# Topic\n\nSearch phrase: %s\n\nScout result (%s):\n```\n%s\n```\n" % (
                    body["topic"], body.get("scout_file", ""), json.dumps(body.get("scout_row", {}), indent=1, ensure_ascii=False)))
        return {"ok": True, "slug": os.path.basename(nd), "out": "Đã tạo video " + os.path.basename(nd)}
    if a == "scout":
        phrases = [p.strip() for p in body.get("phrases", "").splitlines() if p.strip()]
        os.makedirs(os.path.join(research_dir(cid), "scout"), exist_ok=True)
        name = time.strftime("scout_%Y%m%d_%H%M%S")
        path = os.path.join(research_dir(cid), "scout", name + ".txt")
        open(path, "w").write("\n".join("%d|%s" % (i, p) for i, p in enumerate(phrases, 1)) + "\n")
        return start_job(a, [PY, "-u", "tools/research/scout.py", path], "Đo %d cụm từ" % len(phrases))
    if a == "claude":
        return claude_job(body.get("message", ""), d, tag, cid, body.get("model"), body.get("effort"))
    if a == "gemini":
        return gemini_job(body.get("message", ""), d, tag, cid, model=body.get("gmodel"))
    if a == "suggest_phrases":
        cobj = channel(cid)
        ch = cobj["name"]
        if cobj.get("language") == "vi":
            msg = ("Gợi ý %d cụm từ tìm kiếm YouTube / YouTube Shorts bằng tiếng Việt (câu người xem Việt Nam thực sự gõ) "
                   "về cách xây dựng công trình lịch sử hoặc chế tác bảo vật/hiện vật cổ ở Việt Nam cho kênh \"%s\" "
                   "(đã làm Thành Cổ Loa và Bãi cọc Bạch Đằng). %s "
                   "Hãy tìm xu hướng trên web và YouTube trước. Chỉ trả lời ĐÚNG danh sách cụm từ, mỗi dòng một cụm, không đánh số, không giải thích."
                   % (int(body.get("n", 15)), ch, body.get("hint", "")))
        else:
            msg = ("Suggest %d English YouTube search phrases (what US viewers type) for new video topics for the channel \"%s\". %s "
                   "Search the web and YouTube trends first. Reply with ONLY the phrases, one per line, no numbering, no other text."
                   % (int(body.get("n", 15)), ch, body.get("hint", "")))
        return gemini_job(msg, None, None, cid, label="Gemini gợi ý cụm từ", fast=True, save_as="phrases")
    if a == "stop":
        stop_job(body["job"])
        return {"ok": True}
    raise KeyError("unknown action " + str(a))


def save(body):
    d = video_dir(body["channel"], body["slug"])
    target = {
        "script": "script/script.txt",
        "cast": "images/cast.json",
        "shots": "images/shots.json",
        "youtube": "packaging/youtube.txt",
    }[body["what"]]
    if body["what"] in ("cast", "shots"):
        json.loads(body["text"])  # refuse broken JSON
    p = os.path.join(d, target)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(body["text"])
    return {"ok": True}


def gemini_job(message, d, tag, cid, label=None, fast=False, save_as=None, model=None, name=None, query=None):
    """Reading-heavy work for Gemini through the Antigravity CLI (Google plan quota, not Claude's).
    agy cannot write files in headless mode on this account, so the answer comes back as text and is saved here."""
    g = CFG["gemini"]
    work = os.path.join(DASH, "agy_work")
    if not os.path.isdir(os.path.join(work, ".git")):
        os.makedirs(work, exist_ok=True)
        subprocess.run(["git", "init", "-q", work])
    base = d or os.path.join(DASH, "general")
    sdir = os.path.join(base, ".dashboard")
    os.makedirs(sdir, exist_ok=True)
    cobj = channel(cid)
    where = ("Context: YouTube video folder %s of the channel \"%s\". You may read files there (absolute path %s)."
             % (rel(d), cobj["name"], d)) if d else ("Context: the YouTube channel \"%s\", %s." % (cobj["name"], cobj.get("about", "")))
    lang_rule = ("The channel and owner both use Vietnamese: write everything (prose, titles, search phrases) in natural Vietnamese."
                 if cobj.get("language") == "vi"
                 else "The owner reads Vietnamese: write prose answers in Vietnamese, keep titles, search phrases, quotes and sources in English.")
    task = ("%s\n%s Give a source URL for every fact. Do not invent numbers.\n\nREQUEST:\n%s" % (where, lang_rule, message))
    if model not in GEMINI_MODELS:
        model = g["fast_model"] if fast else g["model"]
    cmd = [os.path.expanduser(g["agy"]), "-p", task, "--model", model,
           "--output-format", "json", "--print-timeout", "1800s", "--dangerously-skip-permissions"]
    if d:
        cmd += ["--add-dir", d]
    hist = os.path.join(sdir, "claude.jsonl")
    if not save_as:  # internal requests (phrase suggestions) stay out of the chat history
        with open(hist, "a") as fh:
            fh.write(json.dumps({"role": "owner", "text": "[Gemini] " + (label or message), "at": time.strftime("%H:%M")}, ensure_ascii=False) + "\n")
    buf = []
    body_query = [query]

    def on_line(line):
        buf.append(line)
        return ""

    def on_end(job):
        raw = "".join(buf)
        try:
            res = json.loads(raw[raw.find("{"):])
            text = res.get("response", "").strip()
        except ValueError:
            res, text = {}, raw.strip()[-4000:]
        out = os.path.join(base, "research", "gemini") if d else os.path.join(research_dir(cid), "gemini")
        os.makedirs(out, exist_ok=True)
        fn = os.path.join(out, time.strftime("%Y%m%d_%H%M%S") + ("_phrases.txt" if save_as else ("_%s.md" % name if name else ".md")))
        if not d and body_query[0]:  # remember which phrase a workspace-level result is about
            text = "<!-- query: %s -->\n%s" % (body_query[0], text)
        open(fn, "w", encoding="utf-8").write(text + "\n")
        with open(os.path.join(WS, job["log"]), "a", encoding="utf-8") as fh:
            fh.write(text + "\n\n[Gemini xong: %s s, lưu %s]\n" % (res.get("duration_seconds", "?"), rel(fn)))
        job["result_file"] = rel(fn)
        if not save_as:
            with open(hist, "a") as fh:
                fh.write(json.dumps({"role": "gemini", "text": text or "(không có trả lời)", "at": time.strftime("%H:%M")}, ensure_ascii=False) + "\n")
    return start_job("gemini", cmd, label or ("Gemini: " + message[:60]), tag, cwd=work, on_line=on_line, on_end=on_end)


SIM = os.path.expanduser("~/Documents/AI/.claude/skills/yt-script-retention/references/sim-protocol.md")
PRESETS = {
    "simulate": lambda d, b: (
        "Run the viewer simulation on the script %s (one paragraph = one voice block) following the protocol in %s, in ONE pass. "
        "Report: where viewers would leave and why, confusing sentences, weak hook or payoff, and concrete rewrite suggestions per block. "
        "Do not rewrite the whole script and do not change numbers." % (os.path.join(d, "script", "script.txt"), SIM)),
    "titles": lambda d, b: (
        ("Đọc kịch bản %s của kênh YouTube Shorts Công Trường Lịch Sử. Gợi ý 10 tiêu đề Shorts tiếng Việt (kèm #shorts, dưới 65 ký tự, trung thực với nội dung), "
         "5 phương án chữ ảnh bìa dọc 1080x1920 gồm 2 dòng cực ngắn (LINE 1 màu trắng + LINE 2 màu vàng #FFD23F, tổng 4-6 chữ), và 15 tag tiếng Việt."
         % os.path.join(d, "script", "script.txt"))
        if (d and is_shorts(d)) else
        ("Read the script %s and the cast %s. Draft 10 YouTube title options (max 60 characters, honest, no clickbait the video does not pay off), "
         "5 thumbnail concepts (one picture idea + max 4 words each), and 15 tags. Use only claims that are in the script."
         % (os.path.join(d, "script", "script.txt"), os.path.join(d, "images", "cast.json")))),
    "research_topic": lambda d, b: (
        "Deep research for a possible video on the YouTube search phrase \"%s\". 1) What viewers actually want to know (questions, misconceptions). "
        "2) The 8-12 strongest facts with a primary source URL each (papers, museums, government data); mark anything uncertain. "
        "3) Three possible angles that existing top videos do not cover well. 4) A one-paragraph hook idea that only uses facts from your list."
        "%s" % (b.get("query", ""), (" Save nothing; the answer is stored with video %s." % os.path.basename(d)) if d else "")),
    "competitors": lambda d, b: (
        "Competitor analysis for these YouTube videos or search phrases:\n%s\nFor each top video: title, channel, views, length, how the first 30 seconds hook works, "
        "structure, visual style, what comments praise or complain about. Then: what our video should do differently. Give URLs." % b.get("query", "")),
}
PRESET_LABELS = {"research_topic": "Gemini nghiên cứu chủ đề", "simulate": "Gemini giả lập người xem", "titles": "Gemini nháp tiêu đề, thumbnail, tag", "competitors": "Gemini phân tích đối thủ"}
CLAUDE_TASKS = {
    "write_script": ("viết kịch bản", lambda d: (
        ("Viết kịch bản YouTube Shorts (~80-90 giây, 10 đoạn đánh số [1]..[10], khoảng 320-360 âm tiết) cho video %s của kênh Công Trường Lịch Sử. "
         "Tham khảo văn phong channels/vn-history/test-001-co-loa/script/script.txt và channels/vn-history/002-bach-dang/script/script.txt: "
         "mở đầu 'Hôm nay, bạn sẽ...', đưa người xem vào vai người thợ xưa giải bài toán kỹ thuật từng bước, giọng kể tự nhiên đời thường (dùng 'Đầu tiên' thay vì 'Bước đầu tiên', KHÔNG lặp cụm 'rồi chốt luôn'), "
         "không đọc tên sách/bảo tàng trong lời thoại, kết bằng 1 sự thật khảo cổ bất ngờ còn lại hôm nay. Ghi đầy đủ nguồn sử liệu & khảo cổ vào research/sources_log.csv và chạy python3 tools/shorts/voice_shorts.py %s." % (d, d))
        if is_shorts(d) else
        ("Write the script for the video in %s. Inputs: research/topic.md, every file in research/gemini/ (Gemini drafts: open the source URL "
         "of every fact you use and drop anything you cannot confirm), the workspace CLAUDE.md rules and the yt-script-retention skill "
         "(follow its structure, hook rules, length standard and one-pass simulation; channel 2 may run 8-12 minutes when the sourced beats "
         "support it). The spoken text never names or cites a source (no 'according to ...', no study, museum or agency names read aloud). "
         "Write script/script.txt (one paragraph per voice block, blank line between blocks, a [src: ...] tag in every paragraph "
         "with a number), add one row per spoken fact to research/sources_log.csv and a short research/brief-outline.md. Then reply in "
         "Vietnamese: title idea, length estimate, facts you dropped and why." % d))),
    "fix_script": ("sửa kịch bản theo góp ý người xem", lambda d: (
        "Read the newest viewer-simulation notes in %s/research/gemini/*_simulate.md and apply the changes that make the script better "
        "without adding unsourced facts. Edit script/script.txt only. Reply in Vietnamese with what you changed and what you rejected." % d)),
    "make_shots": ("chia cảnh và tạo prompt ảnh", lambda d: (
        ("Chia kịch bản %s thành khoảng 18-22 cảnh dọc 9:16 và ghi images/shots.json theo chuẩn prompt có cấu trúc của "
         "channels/vn-history/003-dia-dao-cu-chi/images/shot_specs.py + build_shots.py (style_lock, negative, veo_tail; mỗi shot có id, block, "
         "duration (giây đọc ước tính ở 3.88 âm tiết/giây, tách cảnh dài hơn ~5 s), xfade, motion_mode 'ambient' hoặc 'active', route, "
         "style_ref hoặc edit_of, camera, vo, sound; ảnh = \"spec\" (shot, angle, top/middle/bottom, setting, people: who/where/pose/hands/gaze/wear, "
         "props: what/size/where/state, light, must_not) hoặc \"edit\" (keep/change/must_not) cho edit_of; clip = \"motion\" (camera, mover, "
         "action, speed, end, still)). Một thứ chuyển động mỗi clip, dụng cụ phải chạm sẵn vật trong ảnh, ghi đúng số người, không từ mơ hồ. "
         "Đọc trước channels/vn-history/LESSONS.md và áp dụng: tối đa 4 shot active; cảnh cắt lớp có chất lỏng, cận cảnh hoa văn và mặt cắt "
         "rộng nhiều hầm trống thì để ảnh tĩnh (bỏ motion); kích thước so với cơ thể/đồ vật, không dùng mm/cm; vật chính lặp lại nhiều cảnh "
         "(vd trống đồng) làm 1 ảnh key rồi các cảnh sau edit_of hoặc extra_refs từ ảnh đó; thay đổi lớn tách 2 shot (edit_of + dissolve), "
         "không bắt Veo diễn; xe/máy bay đi theo hướng mũi trong ảnh; prompt clip chỉ nêu thứ thấy được và thứ chuyển động. "
         "Sau đó chạy python3 tools/shorts/make_shorts_prompts.py %s --check đến khi báo 0 errors rồi chạy không --check. Trả lời tóm tắt bằng tiếng Việt." % (d, d))
        if is_shorts(d) else
        ("Split the script of %s into shots and write images/cast.json and images/shots.json exactly as tools/imageprompts/README.md "
         "describes (style %s, from the channel's channel.json; one card per character with clothing, colours and one-sided items; pose library; locations; "
         "\"era\" for historical videos; block and sentence per shot from the script paragraphs and their sentence order; about one shot "
         "per sentence; leave_space where numbers will be drawn; \"key\": true for the opening and the climax). Then run "
         "python3 tools/imageprompts/make_prompts.py %s and fix the inputs until it reports 0 errors. Reply in Vietnamese: characters, "
         "number of shots, which images the owner must make by hand in Google Flow." % (d, channel_of(d).get("style", "stickman-v1"), d)))),
    "write_upload": ("viết tiêu đề, mô tả, tag", lambda d: (
        ("Viết packaging/youtube.txt (TITLE (chosen), TITLE (alternatives), DESCRIPTION (không thêm dòng «video minh họa bằng AI…»: nhãn nội dung AI đặt trong cài đặt khi đăng), TAGS, SETTINGS) và packaging/cover.py "
         "cho video %s theo đúng mẫu channels/vn-history/002-bach-dang/packaging/youtube.txt. Chỉ dùng dữ kiện có trong kịch bản. Trả lời bằng tiếng Việt." % d)
        if is_shorts(d) else
        ("Write upload/upload.txt for %s in the same format as channels/median-worker/videos/001-rent-vs-pay/upload/upload.txt (=== TITLE ===, === DESCRIPTION === "
         "between dashed lines with key facts, chapters if render/subtitles.srt exists, and ONE short 'Sources:' line that names the sources "
         "from research/sources_log.csv without any links or URLs), "
         "=== TAGS ===, === UPLOAD SETTINGS ===). Use the yt-packaging skill for the title. Only claims that are in the script. "
         "Reply in Vietnamese with the title." % d))),
}
CLAUDE_MODELS = ("opus", "sonnet", "haiku")


def gfiles(d, name):
    g = os.path.join(d, "research", "gemini")
    return sorted(f for f in os.listdir(g) if f.endswith("_%s.md" % name)) if os.path.isdir(g) else []


def steps(d):
    """The guided path for one video: what is done, what comes next and which button does it."""
    img = os.path.join(d, "images")
    script = read(os.path.join(d, "script", "script.txt"))
    man = load_json(os.path.join(img, "prompts", "manifest.json"), {}).get("items", [])
    scenes = [i for i in man if i["kind"] == "scene"]
    frames = sum(os.path.exists(os.path.join(img, i["save_as"])) for i in scenes)
    renders = [f for f in os.listdir(os.path.join(d, "render")) if f.endswith(".mp4")] if os.path.isdir(os.path.join(d, "render")) else []
    topic = re.search(r"Search phrase: (.+)", read(os.path.join(d, "research", "topic.md")))

    if is_shorts(d):
        script_ok = len(script) > 300 and "First voice block" not in script
        has_tl = os.path.exists(os.path.join(d, "render", "timeline.py"))
        raw_shots = load_json(os.path.join(img, "shots.json"), {}).get("shots", [])
        clips = sum(os.path.exists(os.path.join(d, "clips", i["id"] + ".mp4")) for i in scenes)
        covered = sum(1 for i in scenes if os.path.exists(os.path.join(img, i["save_as"])) or os.path.exists(os.path.join(d, "clips", i["id"] + ".mp4")))
        auto_missing = sum(1 for i in scenes if (i.get("route") != "manual" or flowcli.available()) and not os.path.exists(os.path.join(img, i["save_as"])))
        pdir = os.path.join(d, "audio", "vbee_parts")
        has_p1 = bool(glob.glob(os.path.join(pdir, "part1.*"))) if os.path.isdir(pdir) else False
        has_p2 = bool(glob.glob(os.path.join(pdir, "part2.*"))) if os.path.isdir(pdir) else False
        has_parts_txt = os.path.exists(os.path.join(d, "script", "voiceover_tts", "part1.txt"))
        voice_ok = any(os.path.exists(os.path.join(d, "audio", n)) for n in ("voice_full.wav", "voice_full.mp3"))
        yt_ok = "TITLE" in read(os.path.join(d, "packaging", "youtube.txt")) or "=== TITLE ===" in read(os.path.join(d, "upload", "upload.txt"))
        cover_ok = os.path.exists(os.path.join(d, "packaging", "cover_1080x1920.png"))
        can_cover = os.path.exists(os.path.join(d, "packaging", "cover_frame.png")) or frames > 0
        rv_s = load_json(os.path.join(img, "runs", "review.json"), {})
        crv_s = load_json(os.path.join(img, "runs", "clip_review.json"), {})
        imgs_rv = sum(1 for i in scenes if os.path.exists(os.path.join(img, i["save_as"]))
                      and abs(rv_s.get(i["id"], {}).get("mtime", 0) - os.path.getmtime(os.path.join(img, i["save_as"]))) < 1)
        clips_rv = sum(1 for i in scenes if os.path.exists(os.path.join(d, "clips", i["id"] + ".mp4"))
                       and abs(crv_s.get(i["id"], {}).get("mtime", 0) - os.path.getmtime(os.path.join(d, "clips", i["id"] + ".mp4"))) < 1)
        shot_mode = {s["id"]: s.get("motion_mode") for s in raw_shots}
        flow_st = load_json(os.path.join(img, "runs", "flow_state.json"), {})
        img_ok = load_json(os.path.join(img, "runs", "approvals.json"), {}).get("images", {})

        def img_pass(i):  # start image 5/5 or approved by the owner, for its current file
            p = os.path.join(img, i["save_as"])
            if not os.path.exists(p):
                return False
            m = os.path.getmtime(p)
            r, ap = rv_s.get(i["id"], {}), img_ok.get(i["id"], {})
            return abs(ap.get("mtime", 0) - m) < 1 or (r.get("score", 0) >= PASS and abs(r.get("mtime", 0) - m) < 1)
        clips_final = sum(1 for i in scenes if flow_st.get(i["id"], {}).get("stage") == "done"
                          or (i["id"] not in flow_st and os.path.exists(os.path.join(d, "clips", i["id"] + ".mp4"))))
        asks = sum(1 for f in flow_st.values() if f.get("status") == "ask") + sum(
            1 for i in scenes if rv_s.get(i["id"], {}).get("score") == 3 and i["id"] not in img_ok
            and os.path.exists(os.path.join(img, i["save_as"]))
            and abs(rv_s[i["id"]].get("mtime", 0) - os.path.getmtime(os.path.join(img, i["save_as"]))) < 1)
        flow_ready = sum(1 for i in scenes if i["id"] in shot_mode and img_pass(i)
                         and flow_st.get(i["id"], {}).get("stage") != "done" and flow_st.get(i["id"], {}).get("status") != "ask")
        rrv = load_json(os.path.join(d, "render", "review.json"), None)
        rrv_f = os.path.join(d, rrv.get("file", "")) if isinstance(rrv, dict) else ""
        rrv_ok = bool(rrv and os.path.exists(rrv_f) and abs(rrv.get("mtime", 0) - os.path.getmtime(rrv_f)) < 1)
        need_img_rv = frames > imgs_rv
        need_clip_rv = clips > clips_rv

        S = [
            {"key": "research", "label": "Nghiên cứu", "who": "Gemini", "done": bool(gfiles(d, "research_topic")) or script_ok or bool(scenes),
             "hint": "Tra cứu sử liệu gốc & phát hiện khảo cổ học trước khi lên kịch bản.",
             "action": {"action": "research_topic", "query": topic.group(1) if topic else ""}, "button": "Gemini nghiên cứu", "tab": "script"},
            {"key": "script", "label": "Kịch bản 90s", "who": "Claude + bạn", "done": script_ok,
             "hint": "10 đoạn (~320–360 âm tiết), góc nhìn người thợ xây dựng công trình + cú lật khảo cổ cuối bài.",
             "action": {"action": "write_script"}, "button": "Claude viết kịch bản", "tab": "script"},
            {"key": "shots", "label": "Chia cảnh 9:16", "who": "Code / Claude", "done": bool(scenes) or (has_tl and bool(renders)),
             "hint": "Xuất bộ prompt ảnh 9:16 khóa style Ligne Claire và prompt chuyển động Veo cho từng cảnh.",
             "action": {"action": "prompts"} if raw_shots else {"action": "make_shots"},
             "button": "Tạo prompt 9:16 + Veo" if raw_shots else "Claude chia cảnh 9:16", "tab": "shots"},
            {"key": "scenes", "label": "Ảnh + clip (tự động)", "who": "Gemini + Flow, bạn duyệt",
             "done": (bool(scenes) and frames == len(scenes) and clips_final == len(scenes) and not asks) or (has_tl and bool(renders)),
             "hint": ("%d/%d ảnh · %d/%d clip xong%s. Một nút: tạo ảnh, Gemini kiểm & tự sửa, rồi tạo clip (lite → fast cho cảnh hành động → 1080p). Bạn chỉ duyệt mục 3/5."
                      % (frames, len(scenes), clips_final, len(scenes), (" · %d mục chờ bạn duyệt" % asks) if asks else "")) if scenes else "Tạo ảnh gốc 9:16 cho các cảnh.",
             "action": {"action": "auto_video"} if (auto_missing or flow_ready or need_img_rv) else None,
             "button": "▶ Tạo tự động: ảnh + clip" if (auto_missing or flow_ready or need_img_rv) else
                       ("Mở trang phân cảnh (%d chờ duyệt)" % asks if asks else "Mở trang phân cảnh"), "tab": "shots"},
            {"key": "voice", "label": "Giọng Vbee", "who": "Bạn (Vbee 2 phần)", "done": voice_ok,
             "hint": ("Đã có đủ Part 1 & Part 2 — bấm ghép thành audio/voice_full.wav." if (has_p1 and has_p2)
                      else "Copy part1.txt & part2.txt (<60s/phần) sang Vbee, đặt tốc độ %s, tải 2 file âm thanh lên rồi bấm Ghép." % voice_cfg_of(d)[0]),
             "action": ({"action": "join_voice"} if (has_p1 and has_p2) else (None if has_parts_txt else {"action": "voice_text"})),
             "button": ("Ghép Part 1 + Part 2" if (has_p1 and has_p2) else ("Mở trang Giọng Vbee" if has_parts_txt else "Tách part1 & part2")), "tab": "voice"},
            {"key": "render", "label": "Dựng 9:16", "who": "Code (Swift)", "done": bool(renders),
             "hint": "Tự bắt nhịp ngắt đoạn trong voice_full, ghép clip Veo & ảnh tĩnh thành bản TikTok + YouTube 1080x1920.",
             "action": {"action": "render"}, "button": "Dựng video 9:16", "tab": "preview"},
            {"key": "review_render", "label": "Kiểm bản dựng", "who": "Gemini", "optional": True,
             "done": bool(renders) and rrv_ok,
             "hint": "Gemini kiểm khớp hình – lời cả 10 đoạn, nhịp cắt, độ giật seam Veo và âm lượng LUFS trước khi đăng.",
             "action": {"action": "review_render"} if renders else None,
             "button": "Gemini kiểm bản dựng", "tab": "preview"},
            {"key": "upload", "label": "Ảnh bìa & Đăng", "who": "Code + bạn", "done": yt_ok and cover_ok,
             "hint": "Tạo ảnh bìa dọc 1080x1920 (Be Vietnam Pro vàng/trắng) và copy tiêu đề, mô tả, tag sang YouTube/TikTok.",
             "action": ({"action": "make_cover"} if (yt_ok and not cover_ok and can_cover) else (None if yt_ok else {"action": "write_upload"})),
             "button": ("Tạo ảnh bìa 1080x1920" if (yt_ok and not cover_ok and can_cover) else ("Mở trang Ảnh bìa & Đăng" if yt_ok else "Claude viết tiêu đề & mô tả")), "tab": "upload"},
        ]
        nxt = next((x for x in S if not x["done"] and not x.get("optional")), None)
        return {"steps": S, "next": nxt["key"] if nxt else None}

    script_ok = len(script) > 800 and "First voice block" not in script
    sheets = [i for i in man if i["kind"] != "scene"]
    sheets_ok = sheets and all(os.path.exists(os.path.join(img, i["save_as"])) for i in sheets)
    rv = load_json(os.path.join(img, "runs", "review.json"), {})
    auto_missing = sum(1 for i in scenes if (i.get("route") != "manual" or flowcli.available()) and not os.path.exists(os.path.join(img, i["save_as"])))
    tts_dir = os.path.join(d, "script", "voiceover_tts")
    tts = [f for f in os.listdir(tts_dir) if f.endswith(".txt")] if os.path.isdir(tts_dir) else []
    mp3 = [f for f in tts if os.path.exists(os.path.join(d, "audio", f[:-4] + ".mp3"))]
    S = [
        {"key": "research", "label": "Nghiên cứu", "who": "Gemini", "done": bool(gfiles(d, "research_topic")) or script_ok or bool(scenes),
         "hint": "Gemini gom dữ kiện có nguồn, câu hỏi người xem và góc chưa ai làm.",
         "action": {"action": "research_topic", "query": topic.group(1) if topic else ""}, "button": "Gemini nghiên cứu", "tab": "script"},
        {"key": "script", "label": "Kịch bản", "who": "Claude", "done": script_ok or bool(scenes),
         "hint": "Claude viết kịch bản từ nghiên cứu, kiểm từng nguồn, ghi bảng nguồn. Bạn đọc và sửa ở trang này.",
         "action": {"action": "write_script"}, "button": "Claude viết kịch bản", "tab": "script"},
        {"key": "sim", "label": "Góp ý người xem", "who": "Gemini", "done": bool(gfiles(d, "simulate")) or bool(scenes), "optional": True,
         "hint": "Gemini đóng vai người xem, chỉ ra chỗ chán và khó hiểu. Sau đó có thể nhờ Claude sửa theo góp ý.",
         "action": {"action": "simulate"}, "button": "Gemini giả lập người xem", "tab": "script",
         "extra": {"action": "fix_script", "button": "Claude sửa theo góp ý"} if gfiles(d, "simulate") else None},
        {"key": "shots", "label": "Chia cảnh", "who": "Claude", "done": bool(scenes),
         "hint": "Claude lập danh sách nhân vật và cảnh; bộ tạo prompt tự khóa style và làm bảng nhân vật tổng hợp.",
         "action": {"action": "make_shots"}, "button": "Claude chia cảnh", "tab": "shots"},
        {"key": "sheets", "label": "Bảng nhân vật", "who": "Bạn (Flow)", "done": bool(sheets_ok),
         "hint": "Tạo bảng nhân vật trên Google Flow theo hướng dẫn ở từng mục, kéo ảnh vào rồi bấm Duyệt.",
         "action": None, "button": "Mở trang ảnh", "tab": "shots"},
        {"key": "scenes", "label": "Ảnh cảnh", "who": "Gemini + bạn", "done": bool(scenes) and frames == len(scenes),
         "hint": ("%d/%d cảnh có ảnh. Cảnh quan trọng làm trên Flow; còn lại bấm để Gemini tạo." % (frames, len(scenes))) if auto_missing
                 else "%d/%d cảnh có ảnh. Ảnh tự động đã đủ; còn %d ảnh bạn phải tạo tay trên Flow." % (frames, len(scenes), len(scenes) - frames),
         "action": {"action": "auto_images"} if auto_missing else None,
         "button": "Gemini tạo %d ảnh + tự kiểm, tự sửa" % auto_missing if auto_missing else "Mở trang ảnh", "tab": "shots"},
        {"key": "review", "label": "Kiểm ảnh", "who": "Gemini", "done": bool(scenes) and all(i["id"] in rv for i in scenes), "optional": True,
         "hint": "Gemini so từng ảnh với bảng nhân vật và báo lỗi; ảnh lỗi thì bấm Tạo lại.",
         "action": {"action": "review"}, "button": "Gemini kiểm ảnh", "tab": "shots"},
        {"key": "voice", "label": "Giọng đọc", "who": "Bạn (ElevenLabs)", "done": bool(tts) and len(mp3) == len(tts),
         "hint": "Tạo text giọng, tạo mp3 trên ElevenLabs bằng extension, kéo các file vào trang Giọng đọc." if tts else "Bấm để tạo text cho từng đoạn giọng.",
         "action": None if tts else {"action": "voice_text"}, "button": "Mở trang giọng" if tts else "Tạo text giọng đọc", "tab": "voice"},
        {"key": "render", "label": "Dựng video", "who": "Code", "done": bool(renders),
         "hint": "Ghép ảnh, giọng, chữ và chapter thành video 1440p.", "action": {"action": "render"}, "button": "Dựng video 1440p", "tab": "preview"},
        {"key": "upload", "label": "Đăng", "who": "Claude + bạn", "done": "=== TITLE ===" in read(os.path.join(d, "upload", "upload.txt")),
         "hint": "Claude viết tiêu đề, mô tả, tag; bạn chọn thumbnail rồi copy sang YouTube Studio.",
         "action": {"action": "write_upload"}, "button": "Claude viết tiêu đề, mô tả", "tab": "upload"},
    ]
    nxt = next((x for x in S if not x["done"] and not x.get("optional")), None)
    return {"steps": S, "next": nxt["key"] if nxt else None}
EFFORTS = ("low", "medium", "high", "xhigh", "max")
GEMINI_MODELS = tuple("gemini-%s-%s" % (m, e) for m in ("4-argon", "3.8-flash") for e in ("high", "medium", "low"))


def claude_job(message, d, tag, cid, model=None, effort=None, label=None):
    """Owner's request typed in the dashboard -> Claude Code in headless mode, one resumable session per video."""
    base = d or os.path.join(DASH, "general")
    sdir = os.path.join(base, ".dashboard")
    os.makedirs(sdir, exist_ok=True)
    sfile = os.path.join(sdir, "claude_session")
    sid = read(sfile).strip()
    shorts = is_shorts(d) if d else (is_shorts_ch(channel(cid)) if cid else False)
    where = ("video folder %s (channel %s)" % (rel(d), channel(cid)["name"])) if d else "the workspace (no video selected)"
    tool_hint = ("For 9:16 Shorts (Công Trường Lịch Sử): use tools/shorts/make_shorts_prompts.py, tools/shorts/voice_shorts.py, "
                 "tools/shorts/render_shorts.py, tools/shorts/make_cover.py and tools/gemini/agy_images.py."
                 if shorts else
                 "Character images: only through tools/imageprompts/make_prompts.py and tools/gemini/agy_images.py, never hand-written prompts.")
    sys_prompt = ("You are called from the owner's Studio dashboard. Work on %s. Follow CLAUDE.md and the skills. "
                  "The owner reads Vietnamese: answer briefly in Vietnamese. %s "
                  "Do not publish anything and do not delete videos." % (where, tool_hint))
    cmd = ["claude", "-p", message, "--output-format", "stream-json", "--verbose",
           "--permission-mode", CFG["claude"]["permission_mode"], "--append-system-prompt", sys_prompt,
           "--allowedTools"] + CFG["claude"]["allowed_tools"]
    if model in CLAUDE_MODELS:
        cmd += ["--model", model]
    if effort in EFFORTS:
        cmd += ["--effort", effort]
    if sid:
        cmd += ["--resume", sid]
    else:
        sid = str(uuid.uuid4())
        cmd += ["--session-id", sid]
        open(sfile, "w").write(sid)
    hist = os.path.join(sdir, "claude.jsonl")
    with open(hist, "a") as fh:
        fh.write(json.dumps({"role": "owner", "text": message, "at": time.strftime("%H:%M")}, ensure_ascii=False) + "\n")
    answer = []

    def on_line(line):
        try:
            ev = json.loads(line)
        except ValueError:
            return line
        if ev.get("type") == "assistant":
            out = []
            for c in ev.get("message", {}).get("content", []):
                if c.get("type") == "text":
                    out.append(c["text"])
                    answer.append(c["text"])
                elif c.get("type") == "tool_use":
                    inp = c.get("input", {})
                    out.append("  -> %s %s" % (c.get("name"), (inp.get("command") or inp.get("file_path") or inp.get("pattern") or "")[:160]))
            return "\n".join(out) + "\n" if out else ""
        if ev.get("type") == "result":
            return "\n[xong: %s, %.0f s]\n" % (ev.get("subtype"), (ev.get("duration_ms") or 0) / 1000)
        return ""

    def on_end(job):
        with open(hist, "a") as fh:
            fh.write(json.dumps({"role": "claude", "text": answer[-1] if answer else "(không có trả lời)", "at": time.strftime("%H:%M")}, ensure_ascii=False) + "\n")
    who = "Claude%s%s: " % (" " + model if model in CLAUDE_MODELS else "", " " + effort if effort in EFFORTS else "")
    return start_job("claude", cmd, (who + label) if label else (who + message[:60]), tag, on_line=on_line, on_end=on_end)


# ---------------------------------------------------------------- HTTP
class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        try:
            if u.path in ("/favicon.svg", "/favicon.ico"):  # clapperboard icon for the browser tab
                return self.send(200, open(os.path.join(DASH, "favicon.svg"), "rb").read(), "image/svg+xml")
            if u.path in ("/", "/index.html"):
                return self.send(200, open(os.path.join(DASH, "index.html"), "rb").read(), "text/html; charset=utf-8")
            if u.path == "/api/state":
                return self.send(200, state())
            if u.path == "/api/video":
                return self.send(200, video_detail(q["channel"][0], q["slug"][0]))
            if u.path == "/api/job":
                j = JOBS.get(q["id"][0])
                if not j:
                    return self.send(404, {"error": "no job"})
                txt = read(os.path.join(WS, j["log"]))
                return self.send(200, dict({k: v for k, v in j.items() if k != "proc"}, text=txt[-20000:]))
            if u.path == "/api/scout":
                sd = os.path.join(research_dir(q.get("channel", [channels()[0]["id"]])[0]), "scout")
                files = sorted(f for f in os.listdir(sd) if f.endswith(".csv")) if os.path.isdir(sd) else []
                rows = list(csv.DictReader(open(os.path.join(sd, files[-1]), encoding="utf-8"))) if files else []
                return self.send(200, {"file": files[-1] if files else None, "rows": rows})
            if u.path == "/api/text":
                p = safe(q["path"][0])
                return self.send(200, {"text": read(p) if p else ""})
            if u.path == "/file":
                return self.file(q["path"][0])
        except (KeyError, IndexError) as e:
            return self.send(400, {"error": str(e)})
        self.send(404, {"error": "not found"})

    def file(self, path):
        p = safe(path)
        if not p or not os.path.isfile(p):
            return self.send(404, {"error": "no file"})
        size = os.path.getsize(p)
        ctype = mimetypes.guess_type(p)[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-")
            start = int(a) if a else max(0, size - int(b))
            end = int(b) if a and b else size - 1
        length = end - start + 1
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-cache")
        if rng:
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        self.end_headers()
        with open(p, "rb") as fh:
            fh.seek(start)
            left = length
            while left > 0:
                chunk = fh.read(min(1 << 20, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n)
        try:
            if u.path == "/api/upload":
                return self.send(200, upload(q, raw))
            body = json.loads(raw or b"{}")
            if u.path == "/api/action":
                r = act(body)
                if r.get("status") == "running":  # remember which button/item started it, so the page can show it busy
                    r["action"] = body.get("action")
                    r["item"] = body.get("id") or ",".join(body.get("only") or []) or (body.get("query") or body.get("hint") or "").strip()
                return self.send(200, {k: v for k, v in r.items() if k != "proc"})
            if u.path == "/api/save":
                return self.send(200, save(body))
        except (KeyError, ValueError) as e:
            return self.send(400, {"error": str(e)})
        self.send(404, {"error": "not found"})


def upload(q, raw):
    d = video_dir(q["channel"][0], q["slug"][0])
    kind = q["kind"][0]
    if kind == "voice":  # 01.mp3 ... matched by the number in the file name
        m = re.search(r"(\d{1,2})", q["name"][0])
        if not m or not raw:
            raise ValueError("tên file cần có số đoạn, ví dụ 03.mp3")
        os.makedirs(os.path.join(d, "audio"), exist_ok=True)
        dst = os.path.join(d, "audio", "%02d.mp3" % int(m.group(1)))
        open(dst, "wb").write(raw)
        return {"ok": True, "saved": rel(dst)}
    if kind == "vbee_part":  # Vbee 2-part audio/video upload (part1 or part2)
        part = "part1" if q.get("part", ["1"])[0] in ("1", "part1") else "part2"
        ext = os.path.splitext(q["name"][0])[1].lower() or ".mp3"
        pdir = os.path.join(d, "audio", "vbee_parts")
        os.makedirs(pdir, exist_ok=True)
        for old in glob.glob(os.path.join(pdir, part + ".*")):
            os.remove(old)
        dst = os.path.join(pdir, part + ext)
        open(dst, "wb").write(raw)
        both = bool(glob.glob(os.path.join(pdir, "part1.*"))) and bool(glob.glob(os.path.join(pdir, "part2.*")))
        msg = "Đã lưu %s" % os.path.basename(dst) + (" — đã đủ 2 phần, bấm 'Ghép Part 1 + Part 2' để tạo voice_full.wav" if both else "")
        return {"ok": True, "saved": rel(dst), "out": msg}
    if kind == "voice_full":  # Direct upload of audio/voice_full.wav or .mp3
        ext = os.path.splitext(q["name"][0])[1].lower() or ".wav"
        os.makedirs(os.path.join(d, "audio"), exist_ok=True)
        if ext in (".wav", ".mp3"):
            dst = os.path.join(d, "audio", "voice_full" + ext)
            open(dst, "wb").write(raw)
        else:
            tmp = os.path.join(JOBS_DIR, "vf_" + uuid.uuid4().hex + ext)
            open(tmp, "wb").write(raw)
            dst = os.path.join(d, "audio", "voice_full.wav")
            subprocess.run([FFMPEG_BIN, "-y", "-v", "error", "-i", tmp, "-ac", "2", "-ar", "44100", dst],
                           env=dict(os.environ, DYLD_LIBRARY_PATH=FFMPEG_DIR), check=True)
            os.remove(tmp)
        return {"ok": True, "saved": rel(dst), "out": "Đã lưu " + os.path.basename(dst)}
    if kind == "clip":  # Veo .mp4 clip for one shot id -> VIDEO/clips/<id>.mp4
        sid = re.sub(r"[^\w-]", "", q["id"][0])
        if not sid or not raw:
            raise ValueError("thiếu mã cảnh hoặc file rỗng")
        os.makedirs(os.path.join(d, "clips"), exist_ok=True)
        ext = os.path.splitext(q["name"][0])[1].lower() or ".mp4"
        dst = os.path.join(d, "clips", sid + ".mp4")
        if ext == ".mp4":
            open(dst, "wb").write(raw)
        else:
            tmp = os.path.join(JOBS_DIR, "clip_" + uuid.uuid4().hex + ext)
            open(tmp, "wb").write(raw)
            subprocess.run([FFMPEG_BIN, "-y", "-v", "error", "-i", tmp, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-an", dst],
                           env=dict(os.environ, DYLD_LIBRARY_PATH=FFMPEG_DIR), check=True)
            os.remove(tmp)
        return {"ok": True, "saved": rel(dst), "out": "Đã lưu clip Veo %s.mp4" % sid}
    if kind == "cover_bg":  # 9:16 background frame for packaging/cover_frame.png
        os.makedirs(os.path.join(d, "packaging"), exist_ok=True)
        dst = os.path.join(d, "packaging", "cover_frame.png")
        tmp = os.path.join(JOBS_DIR, "cbg_" + uuid.uuid4().hex + (os.path.splitext(q["name"][0])[1].lower() or ".png"))
        open(tmp, "wb").write(raw)
        subprocess.run(["sips", "-s", "format", "png", tmp, "--out", dst], capture_output=True)
        os.remove(tmp)
        return {"ok": True, "saved": rel(dst), "out": "Đã lưu ảnh nền bìa packaging/cover_frame.png"}
    if kind == "image":  # a hand-made image (Gemini app / Flow) for one manifest item
        ext = os.path.splitext(q["name"][0])[1].lower() or ".png"
        tmp = os.path.join(JOBS_DIR, "upload_" + uuid.uuid4().hex + ext)
        open(tmp, "wb").write(raw)
        p = subprocess.run([PY, "tools/gemini/agy_images.py", d, "--import", q["id"][0], tmp], cwd=WS, capture_output=True, text=True)
        os.remove(tmp)
        return {"ok": p.returncode == 0, "out": p.stdout + p.stderr}
    if kind == "thumbnail":
        os.makedirs(os.path.join(d, "upload"), exist_ok=True)
        dst = os.path.join(d, "upload", "thumbnail.png")
        tmp = os.path.join(JOBS_DIR, "thumb_" + uuid.uuid4().hex + os.path.splitext(q["name"][0])[1].lower())
        open(tmp, "wb").write(raw)
        # YouTube wants 1280x720 and at most 2 MB: cover-fit, centre-crop, PNG (JPEG if the PNG is too big)
        subprocess.run(["sips", "-s", "format", "png", tmp, "--out", dst], capture_output=True)
        os.remove(tmp)
        out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", dst], capture_output=True, text=True).stdout
        w, h = int(re.search(r"pixelWidth: (\d+)", out).group(1)), int(re.search(r"pixelHeight: (\d+)", out).group(1))
        k = max(1280 / w, 720 / h)
        subprocess.run(["sips", "-z", str(round(h * k)), str(round(w * k)), dst], capture_output=True)
        subprocess.run(["sips", "-c", "720", "1280", dst], capture_output=True)
        note = ""
        if os.path.getsize(dst) > 2_000_000:
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "90", dst, "--out", dst[:-4] + ".jpg"], capture_output=True)
            note = " (PNG > 2 MB: dùng upload/thumbnail.jpg khi đăng)"
        return {"ok": True, "out": "Đã lưu thumbnail 1280x720" + note}
    raise ValueError("unknown upload kind")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", CFG.get("port", 8765)))
    threading.Thread(target=reconciler, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print("Studio dashboard: http://127.0.0.1:%d" % port)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
