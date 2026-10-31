"""Render a long-form composition from a project's staged public dir (never the whole workspace).

  python -m tools.longform.render projects/001-bach-dang Spike projects/001-bach-dang/render/spike_1440p.mp4 [--frame 150] [--props '{"boil": true}']
  python -m tools.longform.render lang <project_id> <lang>     the full video of one language (job kind render_lang)
  python -m tools.longform.render still <project_id> <beat>    a preview frame of one beat (job kind render_still)

A language render needs every voice part, that language's timing, a valid scene file and every on-screen label in
that language; otherwise it is refused before Remotion starts, so it never makes a silent or half-translated video.
Missing music or SFX files never block a render: they are left out and shown as warnings.
"""
import argparse
import json
import os
import re
import subprocess
import sys

from tools.longform import (audio_lib, claude_box, inbox, jobs, languages, paths, progress, project, scenes, script, stage,
                            timing)

ANIM = os.path.join(paths.WS, "tools", "anim")
PY = os.path.join(paths.WS, ".venv", "bin", "python")
SPIKE_FILES = ["library/backgrounds/bach-dang-path-01.png", "library/characters/tran-hung-dao", "tools/kit/fonts/BeVietnamPro-ExtraBold.ttf"]
FPS = 30
# Font name in config/languages.json -> CSS family and file (OFL fonts, LICENSES.md). Plan 6 adds Noto Sans JP.
FONTS = {"Be Vietnam Pro": {"family": "BeVietnamPro", "file": "tools/kit/fonts/BeVietnamPro-ExtraBold.ttf"}}
MAP_FILE = "library/maps/vn_region.json"
EST_CPS = 14.0  # characters per second for a preview before the voice exists
EST_GAP = 0.3
BEAT_ID = re.compile(r"^B\d+$")


def command(composition, out, public, frame=None, props=None):
    """props: a dict (sent inline) or the path of a JSON file (Remotion reads it; long videos have big props)."""
    if frame is not None:
        c = ["npx", "remotion", "still", "src/index.ts", composition, out, "--frame=%d" % frame]
    else:  # H.264 at 16 Mbps comes from tools/anim/remotion.config.ts (setting --crf as well is an error)
        c = ["npx", "remotion", "render", "src/index.ts", composition, out, "--codec=h264", "--audio-codec=aac"]
    c += ["--public-dir", public]
    if props:
        c.append("--props=%s" % (props if isinstance(props, str) else json.dumps(props)))
    return c


def type_check():
    """Regenerate kits.generated.ts and type-check the scenes: a pose the kit lacks fails here, not deep in a render."""
    py = os.path.join(paths.WS, ".venv", "bin", "python")
    for cmd, cwd in (([py, "-m", "tools.longform.kit", "ts"], paths.WS), (["npx", "tsc", "--noEmit", "-p", "."], ANIM)):
        if subprocess.run(cmd, cwd=cwd).returncode != 0:
            raise RuntimeError("type check failed: %s" % " ".join(cmd))


def render(project_dir, composition, out, files, frame=None, props=None):
    type_check()
    pub = os.path.abspath(stage.stage(project_dir, files))  # remotion runs in tools/anim: a relative path would miss
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    p = subprocess.run(command(composition, out, pub, frame, props), cwd=ANIM)
    if p.returncode != 0 or not os.path.exists(out):
        raise RuntimeError("remotion failed (exit %s)" % p.returncode)
    return out


# ---------------------------------------------------------------- Longform (Plan 5)
def _rel(path):
    return os.path.relpath(os.path.abspath(path), os.path.abspath(paths.root())).replace(os.sep, "/")


def _pid(pdir):
    return os.path.basename(os.path.normpath(pdir))


def _font(lang):
    name = languages.load_languages()[lang].font
    return FONTS.get(name), name


def _used(doc):
    """Background refs, kit ids, sfx ids, label keys and whether a map is shown, from a scene file."""
    bgs, kits, sfx, keys, has_map = [], [], [], [], False
    for b in (doc or {}).get("beats", {}).values():
        ref = b["background"]["id"]
        if ref not in bgs:
            bgs.append(ref)
        for h in b.get("heroes") or []:
            for k in [h["key"]] + [x["key"] for x in h.get("keys") or []]:
                kid = k.split("/")[0]
                if kid not in kits:
                    kits.append(kid)
        for s in b.get("sfx") or []:
            if s["id"] not in sfx:
                sfx.append(s["id"])
        for c in b.get("cards") or []:
            keys += [k for k in (c.get("text_key"), c.get("text_key2")) if k]
        if b.get("map"):
            has_map = True
            keys += [p["label_key"] for p in b["map"].get("places") or []] + ["modern_map"]
    return bgs, kits, sfx, sorted(set(keys)), has_map


def _usable_audio(audio_id):
    try:
        e = audio_lib.get(audio_id)
    except KeyError:
        return None
    return "library/audio/%s" % e["file"] if audio_lib.usable(e) else None


def check(pdir, lang):
    """Why this language cannot be rendered yet (Vietnamese); empty when it can."""
    meta = project.load_project(pdir)
    if lang not in meta["languages"]:
        return ["dự án không có ngôn ngữ %s" % lang]
    out = []
    parts = timing.load_parts(pdir, lang)
    if not parts:
        out.append("chưa có giọng %s (chưa chuẩn bị các phần giọng)" % lang)
    else:
        out += ["thiếu giọng phần %s" % p for p in timing.missing_parts(pdir, lang)]
    t = timing.load(pdir, lang)
    tpath = os.path.join(pdir, "lang", lang, "timing.json")
    if t is None:
        out.append("chưa dò thời điểm từng câu (%s)" % lang)
    elif parts and any(os.path.getmtime(os.path.join(pdir, "lang", lang, "audio", p["file"])) > os.path.getmtime(tpath)
                       for p in parts if os.path.isfile(os.path.join(pdir, "lang", lang, "audio", p["file"]))):
        out.append("giọng %s đã đổi sau lần dò thời điểm: dò lại" % lang)
    doc = scenes.load(pdir)
    if not doc:
        return out + ["chưa có file cảnh"]
    bad = scenes.validate(pdir, doc)
    if bad:
        return out + bad
    labels = scenes.labels(pdir)
    for k in _used(doc)[3]:
        if not str((labels.get(k) or {}).get(lang) or "").strip():
            out.append("nhãn %s chưa có chữ %s" % (k, lang))
    font, name = _font(lang)
    if font is None or not os.path.isfile(os.path.join(paths.root(), font["file"])):
        out.append("chưa có file font %s cho %s" % (name, lang))
    return out


def warnings(pdir):
    """Things that do not block a render: missing or unlicensed audio, an empty audio library."""
    out = []
    if not audio_lib.entries():
        out.append("Thư viện nhạc/hiệu ứng trống: video sẽ chỉ có giọng")
    doc = scenes.load(pdir) or {}
    ids = [c.get("music") for c in doc.get("chapters") or [] if c.get("music")] + _used(doc)[2]
    for i in ids:
        if _usable_audio(i) is None:
            out.append("âm thanh %s thiếu file hoặc giấy phép: bỏ qua khi render" % i)
    return out


def _voice(pdir, lang, t):
    parts = timing.load_parts(pdir, lang) or []
    starts = {p["part"]: p["start"] for p in (t or {}).get("parts", [])}
    return [{"file": _rel(os.path.join(pdir, "lang", lang, "audio", p["file"])), "start": starts[p["part"]]}
            for p in parts if p["part"] in starts]


def estimated_timing(pdir, lang="vi"):
    """A timing from character counts, for previews before the voice exists (never used for a render)."""
    doc = timing.lang_script(pdir, lang) or {}
    t, beats = 0.0, []
    for ch in doc.get("chapters", []):
        for b in ch.get("beats", []):
            rows = []
            for s in b.get("sentences", []):
                d = max(1.0, len(s.get("text", "")) / EST_CPS)
                rows.append({"id": s["id"], "start": round(t, 3), "end": round(t + d, 3)})
                t += d + EST_GAP
            if rows:
                beats.append({"id": b["id"], "start": rows[0]["start"], "end": rows[-1]["end"], "sentences": rows})
    return {"lang": lang, "duration": round(max(t - EST_GAP, 0.1), 3), "beats": beats, "parts": [], "estimated": True}


def props(pdir, lang, timing_doc=None):
    doc = scenes.load(pdir)
    t = timing_doc or timing.load(pdir, lang)
    bgs, kits, sfx, _, _ = _used(doc)
    backgrounds = {}
    for ref in bgs:
        image = scenes.background_file(pdir, ref)
        kind, _, ident = ref.partition(":")
        g = scenes.library_background(ident) if kind == "library" else {}
        backgrounds[ref] = {"image": image, "horizonY": g.get("horizonY"), "groundY": g.get("groundY"),
                            "heroGround": g.get("heroGround"), "path": g.get("path") or []}
    music = {}
    for c in doc.get("chapters") or []:
        f = _usable_audio(c["music"]) if c.get("music") else None
        if f:
            music[c["id"]] = f
    sfx_files = [{"id": i, "file": _usable_audio(i)} for i in sfx if _usable_audio(i)]
    lscript = timing.lang_script(pdir, lang) or {}
    titles = {c["id"]: c.get("title", "") for c in lscript.get("chapters", [])}
    src = script.load(pdir) or {}
    chapter_card = {c["id"]: bool(c.get("title_card")) for c in doc.get("chapters") or []}
    chapters = [{"id": c["id"], "title": titles.get(c["id"], ""), "beats": [b["id"] for b in c.get("beats", [])],
                 "titleCard": chapter_card.get(c["id"], False)} for c in src.get("chapters", [])]
    anchors = {}
    for ch in src.get("chapters", []):
        for b in ch.get("beats", []):
            n = len(b.get("sentences", []))
            for i, s in enumerate(b.get("sentences", [])):
                anchors[s["id"]] = {"beat": b["id"], "index": i, "count": n}
    font, _ = _font(lang)
    return {"scenes": {"chapters": doc.get("chapters") or [], "beats": doc["beats"]}, "timing": t, "labels": scenes.labels(pdir),
            "lang": lang, "audio": {"voice": _voice(pdir, lang, t) if not t.get("estimated") else [], "music": music, "sfx": sfx_files},
            "chapters": chapters, "anchors": anchors, "backgrounds": backgrounds, "font": font or FONTS["Be Vietnam Pro"]}


def assets(pdir, lang, timing_doc=None):
    """Workspace-relative files the render of this language needs (and nothing else)."""
    p = props(pdir, lang, timing_doc)
    _, kits, _, _, has_map = _used(scenes.load(pdir))
    out = [b["image"] for b in p["backgrounds"].values() if b["image"]]
    out += ["library/characters/%s" % k for k in kits]
    out += [v["file"] for v in p["audio"]["voice"]] + list(p["audio"]["music"].values()) + [s["file"] for s in p["audio"]["sfx"]]
    out.append(p["font"]["file"])
    if has_map:
        out.append(MAP_FILE)
    return list(dict.fromkeys(out))


def _props_file(pdir, name, data):
    d = os.path.join(pdir, ".studio")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return os.path.abspath(path)


def _clock(sec, srt=False):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    if srt:
        return "%02d:%02d:%02d,%03d" % (h, m, s, ms)
    return "%d:%02d:%02d" % (h, m, s) if h else "%d:%02d" % (m, s)


def srt(pdir, lang):
    """One cue per sentence: times from the timing, text from that language's script."""
    t = timing.load(pdir, lang) or {"beats": []}
    text = {s["id"]: s["text"] for _, s in script.sentences(timing.lang_script(pdir, lang) or {})}
    cues = [s for b in t["beats"] for s in b["sentences"]]
    return "\n".join("%d\n%s --> %s\n%s\n" % (i, _clock(s["start"], True), _clock(s["end"], True), text.get(s["id"], ""))
                     for i, s in enumerate(cues, 1))


def chapters_txt(pdir, lang):
    """YouTube chapters: '0:00 Title' per chapter from its first beat's start (the first always at 0:00)."""
    t = timing.load(pdir, lang) or {"beats": []}
    start = {b["id"]: b["start"] for b in t["beats"]}
    lines = []
    for ch in (timing.lang_script(pdir, lang) or {}).get("chapters", []):
        s = next((start[b["id"]] for b in ch.get("beats", []) if b["id"] in start), None)
        if s is None:
            continue
        lines.append("%s %s" % (_clock(0 if not lines else int(s)), ch.get("title", "")))
    return "".join(l + "\n" for l in lines)


def output_path(pdir, lang):
    return os.path.join(pdir, "lang", lang, "render", "%s_%s_1440p.mp4" % (_pid(pdir), lang))


def render_lang(pdir, lang):
    problems = check(pdir, lang)
    if problems:
        raise ValueError("; ".join(problems))
    out = render(pdir, "Longform", output_path(pdir, lang), assets(pdir, lang),
                 props=_props_file(pdir, "props_%s.json" % lang, props(pdir, lang)))
    rdir = os.path.dirname(out)
    with open(os.path.join(rdir, "%s_%s.srt" % (_pid(pdir), lang)), "w", encoding="utf-8") as f:
        f.write(srt(pdir, lang))
    with open(os.path.join(rdir, "chapters.txt"), "w", encoding="utf-8") as f:
        f.write(chapters_txt(pdir, lang))
    progress.set_lang(pdir, lang, "render", "done")
    return out


def preview_path(pdir, beat):
    return os.path.join(pdir, "images", "previews", "%s.png" % beat)


def still_beat(pdir, beat, lang="vi"):
    """images/previews/<beat>.png: the frame in the middle of the beat (estimated timing before the voice exists)."""
    doc = scenes.load(pdir)
    if not doc or beat not in doc.get("beats", {}):
        raise KeyError(beat)
    t = timing.load(pdir, lang) or estimated_timing(pdir, lang)
    used = [b for b in t["beats"] if b["id"] in doc["beats"]]
    i = next((n for n, b in enumerate(used) if b["id"] == beat), None)
    if i is None:
        raise KeyError(beat)
    start = 0.0 if i == 0 else used[i]["start"]
    end = used[i + 1]["start"] if i + 1 < len(used) else t["duration"]
    frame = int(round((start + end) / 2 * FPS))
    p = props(pdir, lang, t)
    p["audio"] = {"voice": [], "music": {}, "sfx": []}
    return render(pdir, "Longform", preview_path(pdir, beat), assets(pdir, lang, t), frame=frame,
                  props=_props_file(pdir, "props_still.json", p))


# ---------------------------------------------------------------- jobs
def _project(params):
    pid = claude_box.check_project(params.get("project"))
    if pid is None:
        raise ValueError("thiếu dự án")
    return pid, os.path.join(paths.projects(), pid)


def _lang_argv(params):
    pid, pdir = _project(params)
    if params.get("lang") not in project.load_project(pdir)["languages"]:
        raise ValueError("dự án không có ngôn ngữ %s" % params.get("lang"))
    return [PY, "-m", "tools.longform.render", "lang", pid, params["lang"]]


def _still_argv(params):
    pid, pdir = _project(params)
    beat = params.get("beat")
    if not isinstance(beat, str) or not BEAT_ID.match(beat) or beat not in (scenes.load(pdir) or {}).get("beats", {}):
        raise ValueError("không có cảnh %s" % beat)
    return [PY, "-m", "tools.longform.render", "still", pid, beat]


def _reason(job):
    lines = [l for l in jobs.read_log(job["id"])[0].splitlines() if l.startswith("lỗi: ")]
    return lines[-1][len("lỗi: "):] if lines else None


def render_end(job):
    pid, pdir = _project(job["params"])
    lang = job["params"]["lang"]
    if job["status"] == "done":
        inbox.add(pid, "render_done", "Đã render %s: %s" % (lang.upper(), _rel(output_path(pdir, lang))),
                  screen="scenes", key="render:%s:%s" % (pid, lang))
    elif job["status"] == "failed":
        why = _reason(job)
        if why:  # same key as the job_failed item: its text now says why
            inbox.add(pid, "job_failed", "Render %s hỏng: %s" % (lang.upper(), why), screen="scenes", key="job:%s" % job["id"],
                      notify_owner=False)


def still_end(job):
    if job["status"] == "failed":
        pid, _ = _project(job["params"])
        why = _reason(job)
        if why:
            inbox.add(pid, "job_failed", "Xem trước %s hỏng: %s" % (job["params"]["beat"], why), screen="scenes",
                      key="job:%s" % job["id"], notify_owner=False)


jobs.register(jobs.Kind("render_lang", "render", _lang_argv, on_end=render_end))
jobs.register(jobs.Kind("render_still", "render", _still_argv, on_end=still_end))


def _job_main(argv):
    cmd, pid, arg = argv
    try:
        pdir = os.path.join(paths.projects(), claude_box.check_project(pid))
        out = render_lang(pdir, arg) if cmd == "lang" else still_beat(pdir, arg)
    except (ValueError, RuntimeError, KeyError, OSError) as e:
        print("lỗi: %s" % e, flush=True)
        return 1
    print(out, flush=True)
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] in ("lang", "still"):
        sys.exit(_job_main(sys.argv[1:]))
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("composition")
    ap.add_argument("out")
    ap.add_argument("--frame", type=int)
    ap.add_argument("--props")
    a = ap.parse_args()
    print(render(a.project, a.composition, a.out, SPIKE_FILES, a.frame, json.loads(a.props) if a.props else None))
