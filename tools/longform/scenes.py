"""The scene file: what is on screen in every beat, shared by every language (spec §4.6–4.7).

  scenes/scenes.json   {"version", "updated_by", "updated_at",
                        "chapters": [{"id": "C01", "music": "<audio id>"|null, "title_card": true}],
                        "beats": {"B01": {"background": {"id": "library:<id>"|"project:<item id>",
                                                         "camera": {"from": {"zoom", "x", "y"}, "to": {...}}},
                                          "heroes": [{"key": "kit/pose", "x", "enter": "left|right|none",
                                                      "keys": [{"sentence", "key"}]}],
                                          "crowds": [{"faction", "count", "path": "background"|[[x, y], ...], "speed"}],
                                          "cards": [{"type": "date|name|two_source|chapter", "sentence", "text_key",
                                                     "text_key2" (two_source only)}],
                                          "map": null | {"bbox", "places": [{"label_key", "lon", "lat"}],
                                                         "arrows": [{"from", "to", "sentence"}],
                                                         "areas": [{"points", "fact", "type": "area|border"}]},
                                          "sfx": [{"sentence", "id", "offset", "gain"}]}}}
  scenes/versions/vNNN.json   earlier versions
  scenes/labels.json   {"<label id>": {"vi": "...", "en": "...", ...}}: every on-screen text, per language

Sentence ids in the scene file are source-language (vi) ids; other languages map them by position inside the beat
(see tools/anim/src/longform/timeline.ts). Job kind claude_scenes: Claude writes the file from the approved script and
the approved images, inside its own run folder; on_end validates it whole before saving.
"""
import fcntl
import json
import os
import shutil
import time
from contextlib import contextmanager

from tools.longform import (audio_lib, factbank, images, inbox, jobs, library_index, paths, progress, script, timing,
                            workers)

CARD_TYPES = ("date", "name", "two_source", "chapter")
ENTER = ("left", "right", "none")
FACTIONS = ("daiviet", "nguyen")
AREA_TYPES = ("area", "border")
MAX_SFX = 3
MAX_GAIN = 0.6
W, H = 2560, 1440
# Fixed interface texts (not facts), present in every scene file's labels.
BUILTIN_LABELS = {"modern_map": {"vi": "Bản đồ hiện đại", "en": "Modern map", "ja": "現代の地図", "de": "Heutige Karte",
                                 "es": "Mapa actual"}}


def _dir(pdir, *parts):
    return os.path.join(pdir, "scenes", *parts)


def load(pdir):
    try:
        with open(_dir(pdir, "scenes.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def own_labels(pdir):
    try:
        with open(_dir(pdir, "labels.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def labels(pdir):
    """Labels of the project with the built-in interface texts filled in."""
    out = {k: dict(v) for k, v in BUILTIN_LABELS.items()}
    for k, v in own_labels(pdir).items():
        out[k] = dict(out.get(k, {}), **v) if isinstance(v, dict) else v
    return out


# ---------------------------------------------------------------- references the validator knows
def kit_keys():
    keys = set()
    for c in library_index.summary()["characters"]:
        try:
            with open(os.path.join(paths.library(), "characters", c["id"], "kit.json"), encoding="utf-8") as f:
                keys |= {"%s/%s" % (c["id"], k) for k in (json.load(f).get("images") or {})}
        except (OSError, ValueError):
            continue
    return keys


def library_background(bg_id):
    """Geometry sidecar of a library background ({} when it has none)."""
    try:
        with open(os.path.join(paths.library(), "backgrounds", bg_id + ".json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def background_file(pdir, ref):
    """Workspace-relative image file of a background reference, or None when it is unknown or not approved."""
    kind, _, ident = str(ref or "").partition(":")
    if kind == "library":
        if ident and "/" not in ident and os.path.isfile(os.path.join(paths.library(), "backgrounds", ident + ".png")):
            return "library/backgrounds/%s.png" % ident
        return None
    if kind == "project":
        for it in images.load(pdir):
            if it["id"] == ident and it["type"] == "bg" and it["state"] == "approved" and (it.get("files") or {}).get("final"):
                return it["files"]["final"]
    return None


def _num(v, lo=None, hi=None):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    return (lo is None or v >= lo) and (hi is None or v <= hi)


def _label_ok(lbls, key):
    return isinstance(key, str) and key in lbls


def _beat(pdir, bid, b, sids, kits, audio, facts, lbls, out):
    p = lambda msg: out.append("%s: %s" % (bid, msg))
    if not isinstance(b, dict):
        return p("cảnh hỏng (phải là một object)")
    bg = b.get("background")
    if not isinstance(bg, dict):
        p("thiếu nền")
        bg = {}
    ref = bg.get("id")
    if background_file(pdir, ref) is None:
        p("không có nền %s (thư viện hoặc ảnh dự án đã duyệt)" % ref)
    cam = bg.get("camera") or {}
    for end in ("from", "to"):
        c = cam.get(end) if isinstance(cam, dict) else None
        if not isinstance(c, dict) or not _num(c.get("zoom"), 1, 2) or not _num(c.get("x"), -W, W) or not _num(c.get("y"), -H, H):
            p("camera %s phải có zoom 1–2, x, y" % end)
    sentence = lambda s: s in sids
    heroes = b.get("heroes") or []
    if not isinstance(heroes, list):
        p("heroes phải là danh sách")
        heroes = []
    for h in heroes:
        if not isinstance(h, dict):
            p("nhân vật hỏng")
            continue
        if h.get("key") not in kits:
            p("không có tư thế %s trong bộ nhân vật" % h.get("key"))
        if not _num(h.get("x"), 0, W):
            p("nhân vật %s: x phải trong 0–%d" % (h.get("key"), W))
        if h.get("enter", "none") not in ENTER:
            p("nhân vật %s: enter phải là left, right hoặc none" % h.get("key"))
        for k in h.get("keys") or []:
            if not isinstance(k, dict):
                p("đổi tư thế hỏng")
                continue
            if k.get("key") not in kits:
                p("không có tư thế %s trong bộ nhân vật" % k.get("key"))
            if not sentence(k.get("sentence")):
                p("không có câu %s trong cảnh này" % k.get("sentence"))
    crowds = b.get("crowds") or []
    for c in crowds if isinstance(crowds, list) else [None]:
        if not isinstance(c, dict):
            p("đám đông hỏng")
            continue
        if c.get("faction") not in FACTIONS:
            p("đám đông: phe %s không có (%s)" % (c.get("faction"), ", ".join(FACTIONS)))
        if not isinstance(c.get("count"), int) or not 1 <= c["count"] <= 80:
            p("đám đông: count phải 1–80")
        if not _num(c.get("speed"), 0, 0.02):
            p("đám đông: speed phải 0–0.02")
        path = c.get("path")
        if path == "background":
            kind, _, ident = str(ref or "").partition(":")
            if kind != "library" or len(library_background(ident).get("path") or []) < 2:
                p("đám đông theo đường đi của nền, nhưng nền %s không có đường đi" % ref)
        elif not (isinstance(path, list) and len(path) >= 2 and all(isinstance(q, list) and len(q) == 2 and _num(q[0]) and _num(q[1]) for q in path)):
            p("đám đông: path phải là \"background\" hoặc danh sách điểm [x, y]")
    for c in b.get("cards") or []:
        if not isinstance(c, dict):
            p("thẻ chữ hỏng")
            continue
        if c.get("type") not in CARD_TYPES:
            p("thẻ chữ: loại %s không có" % c.get("type"))
        if not sentence(c.get("sentence")):
            p("không có câu %s trong cảnh này" % c.get("sentence"))
        if not _label_ok(lbls, c.get("text_key")):
            p("không có nhãn chữ %s" % c.get("text_key"))
        if c.get("type") == "two_source" and not _label_ok(lbls, c.get("text_key2")):
            p("thẻ hai nguồn cần text_key2 (nhãn %s không có)" % c.get("text_key2"))
    m = b.get("map")
    if m is not None:
        if not isinstance(m, dict):
            p("bản đồ hỏng")
        else:
            bb = m.get("bbox")
            if not (isinstance(bb, list) and len(bb) == 4 and all(_num(v) for v in bb) and bb[0] < bb[2] and bb[1] < bb[3]):
                p("bản đồ: bbox phải là [lon0, lat0, lon1, lat1]")
            for pl in m.get("places") or []:
                if not isinstance(pl, dict) or not _label_ok(lbls, pl.get("label_key")) or not _num(pl.get("lon")) or not _num(pl.get("lat")):
                    p("bản đồ: địa danh hỏng hoặc không có nhãn %s" % (pl.get("label_key") if isinstance(pl, dict) else pl))
            for a in m.get("arrows") or []:
                if not isinstance(a, dict) or not sentence(a.get("sentence")):
                    p("bản đồ: mũi tên gắn câu %s không có trong cảnh này" % (a.get("sentence") if isinstance(a, dict) else a))
            for ar in m.get("areas") or []:
                if not isinstance(ar, dict) or not isinstance(ar.get("points"), list) or len(ar["points"]) < 3:
                    p("bản đồ: vùng cần ít nhất 3 điểm")
                    continue
                if ar.get("type", "area") not in AREA_TYPES:
                    p("bản đồ: loại vùng %s không có" % ar.get("type"))
                fid = ar.get("fact")
                if fid is not None and fid not in facts:
                    p("bản đồ: không có dữ kiện %s (đã kiểm) trong ngân hàng" % fid)
                if ar.get("type") == "border" and fid is None:
                    p("bản đồ: đường biên giới lịch sử cần một dữ kiện mô tả nó")
    sfx = b.get("sfx") or []
    if not isinstance(sfx, list):
        p("sfx phải là danh sách")
        sfx = []
    if len(sfx) > MAX_SFX:
        p("tối đa 3 hiệu ứng âm thanh mỗi cảnh (có %d)" % len(sfx))
    for s in sfx:
        if not isinstance(s, dict):
            p("hiệu ứng hỏng")
            continue
        if s.get("id") not in audio["sfx"]:
            p("không có hiệu ứng âm thanh %s trong thư viện" % s.get("id"))
        if not sentence(s.get("sentence")):
            p("không có câu %s trong cảnh này" % s.get("sentence"))
        if not _num(s.get("offset", 0), -2, 10):
            p("hiệu ứng %s: offset phải -2–10 giây" % s.get("id"))
        if not _num(s.get("gain"), 0.01, MAX_GAIN):
            p("hiệu ứng %s: gain phải 0.01–%.1f (nhẹ, dưới giọng)" % (s.get("id"), MAX_GAIN))


def _card_numbers(bid, b, sents, allfacts, lbls, out):
    """Every number on a card (vi label) must be in its sentence or in the facts that sentence links."""
    for c in b.get("cards") or []:
        if not isinstance(c, dict) or c.get("sentence") not in sents:
            continue
        s = sents[c["sentence"]]
        known = set(script.digit_groups(s.get("text", "")))
        for fid in s.get("facts", []):
            f = allfacts.get(fid) or {}
            known.update(script.digit_groups("%s %s" % (f.get("claim", ""), f.get("quote", ""))))
        for key in (c.get("text_key"), c.get("text_key2")):
            v = lbls.get(key)
            missing = [n for n in script.digit_groups(v.get("vi") if isinstance(v, dict) else "") if n not in known]
            if missing:
                out.append("%s: thẻ chữ %s có số %s không có trong câu %s hay dữ kiện của câu"
                           % (bid, key, ", ".join(missing), c["sentence"]))


def validate(pdir, data, lbls=None):
    """Problems (Vietnamese) that refuse the scene file; empty when it can be saved and rendered.
    lbls: the labels to check against (default: the project's labels.json)."""
    out = []
    lbls = dict(BUILTIN_LABELS, **(lbls if isinstance(lbls, dict) else own_labels(pdir)))
    for k, v in lbls.items():
        if not isinstance(v, dict) or not str(v.get("vi") or "").strip():
            out.append("nhãn %s không có chữ tiếng Việt (vi)" % k)
    doc = script.load(pdir)
    if not doc:
        return out + ["chưa có kịch bản"]
    if not isinstance(data, dict) or not isinstance(data.get("beats"), dict):
        return out + ["file cảnh hỏng: thiếu beats"]
    beat_sids, beat_sents, chapter_ids = {}, {}, []
    for ch in doc.get("chapters", []):
        chapter_ids.append(ch["id"])
        for b in ch.get("beats", []):
            beat_sids[b["id"]] = {s["id"] for s in b.get("sentences", [])}
            beat_sents[b["id"]] = {s["id"]: s for s in b.get("sentences", [])}
    idx = audio_lib.load()
    audio = {"music": {e["id"] for e in idx["music"]}, "sfx": {e["id"] for e in idx["sfx"]}}
    allfacts = factbank.load(pdir)[1]
    facts = {f["id"] for f in allfacts.values() if f["status"] in workers.USABLE}
    kits = kit_keys()
    chapters = data.get("chapters") or []
    if not isinstance(chapters, list):
        out.append("chapters phải là danh sách")
        chapters = []
    for ch in chapters:
        if not isinstance(ch, dict) or ch.get("id") not in chapter_ids:
            out.append("không có chương %s trong kịch bản" % (ch.get("id") if isinstance(ch, dict) else ch))
            continue
        if ch.get("music") is not None and ch["music"] not in audio["music"]:
            out.append("%s: không có nhạc %s trong thư viện" % (ch["id"], ch["music"]))
    for bid in beat_sids:
        if bid not in data["beats"]:
            out.append("%s: cảnh trong kịch bản chưa có trong file cảnh" % bid)
    for bid, b in data["beats"].items():
        if bid not in beat_sids:
            out.append("%s: không có cảnh này trong kịch bản đã chốt" % bid)
            continue
        try:
            _beat(pdir, bid, b, beat_sids[bid], kits, audio, facts, lbls, out)
            _card_numbers(bid, b, beat_sents[bid], {k: v for k, v in allfacts.items() if k in facts}, lbls, out)
        except (TypeError, AttributeError, KeyError, ValueError) as e:
            out.append("%s: cảnh hỏng (%s)" % (bid, e))
    return out


# ---------------------------------------------------------------- save (versioned, locked)
@contextmanager
def _locked(pdir):
    os.makedirs(_dir(pdir), exist_ok=True)
    with open(_dir(pdir, ".lock"), "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(path + ".tmp", path)


def _merge_labels(old, new):
    """New labels over old ones: a key whose vi text is unchanged keeps its translations; a key whose vi text changed
    keeps only vi (agy_labels writes the other languages again, so a stale translation is never rendered)."""
    out = {}
    for k, v in new.items():
        o = old.get(k)
        if isinstance(v, dict) and isinstance(o, dict) and "vi" in v:
            out[k] = dict(o, **v) if o.get("vi") == v["vi"] else {"vi": v["vi"]}
        else:
            out[k] = v
    return out


def save(pdir, data, by, base=None, labels=None):
    """Save a new version (and, when given, the labels); returns the version number. base: the version this edit
    started from; a newer file on disk refuses the save."""
    with _locked(pdir):
        old = load(pdir)
        cur = (old or {}).get("version", 0)
        if base is not None and cur != base:
            raise ValueError("file cảnh đã đổi (v%d) từ khi bản này bắt đầu (v%d)" % (cur, base))
        if old:
            _write(_dir(pdir, "versions", "v%03d.json" % cur), old)
        data = dict(data, version=cur + 1, updated_by=by, updated_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
        _write(_dir(pdir, "scenes.json"), data)
        if labels is not None:
            _write(_dir(pdir, "labels.json"), _merge_labels(own_labels(pdir), labels))
    return cur + 1


def set_lang_labels(pdir, lang, texts):
    """Merge one language's on-screen texts into labels.json (locked); every existing label id must get a text."""
    with _locked(pdir):
        lbls = own_labels(pdir)
        missing = [k for k in lbls if not isinstance(texts.get(k), str) or not texts[k].strip()]
        if missing:
            raise ValueError("thiếu nhãn: %s" % ", ".join(missing))
        long = [k for k in lbls if len(texts[k]) > 120]
        if long:
            raise ValueError("nhãn dài quá 120 ký tự: %s" % ", ".join(long))
        nums = [k for k in lbls if sorted(script.digit_groups(texts[k])) != sorted(script.digit_groups(lbls[k].get("vi", "")))]
        if nums:
            raise ValueError("số trong nhãn phải giữ đúng như tiếng Việt: %s" % "; ".join(
                "%s (vi: %s; %s: %s)" % (k, " ".join(script.digit_groups(lbls[k].get("vi", ""))) or "không có số", lang,
                                         " ".join(script.digit_groups(texts[k])) or "không có số") for k in nums))
        for k in lbls:
            lbls[k] = dict(lbls[k], **{lang: texts[k].strip()})
        _write(_dir(pdir, "labels.json"), lbls)
    return lbls


def update_beat(pdir, bid, fn, by):
    """Locked read-modify-write of one beat: fn(beat) -> beat; refused when the result does not validate."""
    with _locked(pdir):
        cur = load(pdir)
        if not cur or bid not in cur.get("beats", {}):
            raise KeyError(bid)
        new = json.loads(json.dumps(cur))
        new["beats"][bid] = fn(new["beats"][bid])
        problems = [p for p in validate(pdir, new) if p.startswith(bid + ":")]
        if problems:
            raise ValueError("; ".join(problems))
        _write(_dir(pdir, "versions", "v%03d.json" % cur["version"]), cur)
        new.update(version=cur["version"] + 1, updated_by=by, updated_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
        _write(_dir(pdir, "scenes.json"), new)
        return new


# ---------------------------------------------------------------- claude_scenes job
def _kits_listing():
    out = []
    for c in library_index.summary()["characters"]:
        try:
            with open(os.path.join(paths.library(), "characters", c["id"], "kit.json"), encoding="utf-8") as f:
                k = json.load(f)
        except (OSError, ValueError):
            continue
        out.append({"id": c["id"], "name": k.get("name", c["id"]), "height": k.get("height"),
                    "poses": sorted(k.get("images") or {})})
    return out


def _library_listing():
    s = library_index.summary()
    bgs = []
    for b in s["backgrounds"]:
        g = library_background(b["id"])
        bgs.append({"id": "library:" + b["id"], "horizonY": g.get("horizonY"), "groundY": g.get("groundY"),
                    "heroGround": g.get("heroGround"), "has_path": len(g.get("path") or []) >= 2})
    return {"backgrounds": bgs, "characters": s["characters"]}


def build(params):
    pid, pdir = workers._project(params)
    doc = script.load(pdir)
    if not doc or not doc.get("approved"):
        raise ValueError("kịch bản chưa chốt: chốt kịch bản trước khi dựng cảnh")
    approved = [it for it in images.load(pdir) if it["state"] == "approved"]
    if not approved:
        raise ValueError("chưa có ảnh nào được duyệt")
    audio_lib.warn_if_empty(pid)
    run = workers._new_run(pdir, "claude_scenes")
    os.makedirs(os.path.join(run, "thumbs"))
    rows = []
    for it in approved:
        row = {"id": it["id"], "type": it["type"], "beat": it.get("beat"), "kit": it.get("kit"), "pose_key": it.get("pose_key"),
               "setting": (it.get("spec") or {}).get("setting", ""), "reuse": it.get("reuse"), "thumb": None}
        try:
            src = images.thumb(pdir, it["id"])
            row["thumb"] = os.path.join("thumbs", os.path.basename(src))
            shutil.copyfile(src, os.path.join(run, row["thumb"]))
        except (KeyError, OSError):
            pass
        rows.append(row)
    workers._json_file(os.path.join(run, "script.json"), doc)
    workers._json_file(os.path.join(run, "images.json"), rows)
    workers._json_file(os.path.join(run, "kits.json"), _kits_listing())
    workers._json_file(os.path.join(run, "library.json"), _library_listing())
    workers._json_file(os.path.join(run, "audio.json"), audio_lib.load())
    workers._json_file(os.path.join(run, "facts.json"),
                       [{"id": f["id"], "claim": f["claim"]} for f in workers._fact_rows(pdir, statuses=workers.USABLE)])
    workers._json_file(os.path.join(run, "labels.json"), own_labels(pdir))
    cur = load(pdir)
    if cur:
        workers._json_file(os.path.join(run, "current_scenes.json"), cur)
    t = timing.load(pdir, "vi")
    if t:
        workers._json_file(os.path.join(run, "timing.json"), t)
    workers._task(run, "SCENES.md", "scenes.md", pdir)
    params["run"] = run
    params["base_version"] = (cur or {}).get("version", 0)
    return workers._claude_argv("SCENES.md")


def on_end(job):
    if job["status"] != "done":
        return
    data = workers._result(job, screen="scenes")
    if data is None:
        return
    pid, pdir = workers._project(job["params"])
    if not isinstance(data, dict) or not isinstance(data.get("scenes"), dict) or not isinstance(data.get("labels"), dict):
        return workers._refuse(job, "result.json cần scenes và labels", "scenes")
    problems = validate(pdir, data["scenes"], data["labels"])
    if problems:
        more = " (và %d lỗi khác)" % (len(problems) - 12) if len(problems) > 12 else ""
        return workers._refuse(job, "; ".join(problems[:12]) + more, "scenes")
    try:
        v = save(pdir, data["scenes"], "claude", base=job["params"].get("base_version"), labels=data["labels"])
    except ValueError as e:
        return workers._refuse(job, str(e), "scenes")
    progress.set_step(pdir, "scenes", "wait")
    inbox.add(pid, "scenes_ready", "Cảnh v%d đã dựng xong, chờ bạn xem bảng cảnh" % v, screen="scenes", key="scenes:%s" % pid)


def _guarded(job):
    workers.claude_box._answers.pop(job["id"], None)
    try:
        on_end(job)
    except Exception as e:  # noqa: BLE001  a crash while importing becomes a "Cần bạn" item
        workers._refuse(job, "lỗi khi nhập kết quả: %s" % e, "scenes")


jobs.register(jobs.Kind("claude_scenes", "claude", build, cwd=workers._cwd, on_line=workers.claude_box.on_line, on_end=_guarded))
