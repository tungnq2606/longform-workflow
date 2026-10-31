"""Voice parts per language. The owner makes the voice by hand on the web (Vbee for vi, ElevenLabs for the others);
Studio prepares the text of each part and its file name, then takes the mp3 files back.

  lang/<code>/audio/parts.json       [{"part": "01", "file": "parts/01.mp3", "sentences": [...], "chars", "seconds", "flags"}]
                                     (Plan 5 timing reads part, file (relative to audio/) and sentences)
  lang/<code>/audio/parts/NN.txt     the text to paste
  lang/<code>/audio/parts/NN.mp3     the owner's file

A part stays under the tool limit (Vbee: ~55 s, it inserts a system sentence past ~1 min; ElevenLabs: 4,500
characters). A sentence is never split: one longer than the limit becomes its own part, flagged to cut by hand.
When every part is present, the timing job (Plan 5 kind timing_build, lane cpu) is queued.
"""
import json
import os
import re
import time

from tools.longform import inbox, jobs, languages, progress, script

MAX_BYTES = 50 * 1024 * 1024
ENGINES = {"vbee": "Vbee", "elevenlabs": "ElevenLabs"}
STALE = "phần giọng cũ, chuẩn bị lại"


def _get(cfg, key):
    return cfg.get(key) if isinstance(cfg, dict) else getattr(cfg, key, None)


def _engine(cfg):
    e = _get(cfg, "voice_engine") or ""
    return ENGINES.get(e, e)


def split(sentences, lang_cfg):
    """Greedy packing of (id, text) sentences into parts within the language's limit."""
    cps = float(_get(lang_cfg, "chars_per_second") or 15.0)
    max_s, max_c = _get(lang_cfg, "max_part_seconds"), _get(lang_cfg, "max_part_chars")

    def fits(text):
        return (max_s is None or len(text) / cps <= max_s) and (max_c is None or len(text) <= max_c)

    groups = []
    for sid, text in sentences:
        if groups and fits("\n".join(t for _, t in groups[-1] + [(sid, text)])):
            groups[-1].append((sid, text))
        else:
            groups.append([(sid, text)])
    parts = []
    for n, g in enumerate(groups, 1):
        text = "\n".join(t for _, t in g)
        flags = []
        if not fits(text):  # only a single sentence can be over: it got its own part
            limit = "%s s" % max_s if max_s is not None and len(text) / cps > max_s else "%s ký tự" % max_c
            flags.append("câu %s dài hơn giới hạn %s (%s), cắt bằng tay" % (g[0][0], _engine(lang_cfg), limit))
        parts.append({"part": "%02d" % n, "sentences": [sid for sid, _ in g], "text": text,
                      "seconds": round(len(text) / cps, 1), "flags": flags})
    return parts


def _audio(pdir, lang):
    return os.path.join(pdir, "lang", lang, "audio")


def _parts_dir(pdir, lang):
    return os.path.join(_audio(pdir, lang), "parts")


def load_parts(pdir, lang):
    try:
        with open(os.path.join(_audio(pdir, lang), "parts.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _write_json(path, data):
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(path + ".tmp", path)


def _pid(pdir):
    return os.path.basename(os.path.normpath(pdir))


def _key(pdir, lang):
    return "voice:%s:%s" % (_pid(pdir), lang)


def _sentences(pdir, lang):
    data = script.load(pdir, lang)
    return [(s["id"], s["text"]) for _, s in script.sentences(data or {})], data


def prepare(pdir, lang):
    """Write the part texts and parts.json, and ask the owner for the voice. Refuses until the script is approved."""
    sents, data = _sentences(pdir, lang)
    if not data or not data.get("approved"):
        raise ValueError("kịch bản %s chưa chốt: chốt trước khi làm giọng" % lang.upper())
    cfg = languages.load_languages()[lang]
    parts = split(sents, cfg)
    pdir_parts = _parts_dir(pdir, lang)
    os.makedirs(pdir_parts, exist_ok=True)
    old = load_parts(pdir, lang) or []
    if [p["sentences"] for p in old] != [p["sentences"] for p in parts]:  # different parts: move the old files away
        stash = os.path.join(pdir_parts, "old", time.strftime("%Y%m%d-%H%M%S"))
        for name in os.listdir(pdir_parts):
            if re.fullmatch(r"\d{2}\.(mp3|txt)", name):
                os.makedirs(stash, exist_ok=True)
                os.replace(os.path.join(pdir_parts, name), os.path.join(stash, name))
    rows = []
    for p in parts:
        with open(os.path.join(pdir_parts, p["part"] + ".txt"), "w", encoding="utf-8") as f:
            f.write(p["text"])
        rows.append({"part": p["part"], "file": "parts/%s.mp3" % p["part"], "sentences": p["sentences"],
                     "chars": len(p["text"]), "seconds": p["seconds"], "flags": p["flags"]})
    _write_json(os.path.join(_audio(pdir, lang), "parts.json"), rows)
    progress.set_lang(pdir, lang, "voice", "wait")
    inbox.add(_pid(pdir), "voice_needed", "Giọng %s: %d phần chờ bạn tạo (%s)" % (lang.upper(), len(rows), _engine(cfg)),
              screen="langs", key=_key(pdir, lang))
    return rows


def status(pdir, lang):
    parts = load_parts(pdir, lang) or []
    sents, _ = _sentences(pdir, lang)
    order = [sid for sid, _ in sents]
    stale = bool(parts) and [sid for p in parts for sid in p["sentences"]] != order
    rows = [{"part": p["part"], "file": p["file"], "chars": p.get("chars"), "seconds": p.get("seconds"),
             "flags": p.get("flags", []), "present": os.path.isfile(os.path.join(_audio(pdir, lang), p["file"]))} for p in parts]
    return {"parts": rows, "missing": [r["part"] for r in rows if not r["present"]], "stale": stale,
            "stale_text": STALE if stale else ""}


def part_text(pdir, lang, part):
    """Path of the text file of a known part, else ValueError."""
    if not any(p["part"] == part for p in load_parts(pdir, lang) or []):
        raise ValueError("không có phần %s" % part)
    return os.path.join(_parts_dir(pdir, lang), part + ".txt")


def _is_mp3(data):
    return data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0)


def drop(pdir, lang, name, data):
    """Save the owner's mp3 for one part; when all parts are present, queue the timing."""
    parts = load_parts(pdir, lang) or []
    m = re.fullmatch(r"(\d{2})\.mp3", name or "")
    if not m or not any(p["part"] == m.group(1) for p in parts):
        known = ", ".join(p["part"] + ".mp3" for p in parts) or "chưa chuẩn bị phần nào"
        raise ValueError("tên file %s không phải một phần giọng %s (%s)" % (name, lang.upper(), known))
    if not isinstance(data, (bytes, bytearray)) or not _is_mp3(data):
        raise ValueError("%s không phải file mp3" % name)
    if len(data) > MAX_BYTES:
        raise ValueError("%s quá lớn (tối đa 50 MB)" % name)
    st = status(pdir, lang)
    if st["stale"]:
        raise ValueError("kịch bản đã đổi: %s" % STALE)
    path = os.path.join(_parts_dir(pdir, lang), name)
    with open(path + ".tmp", "wb") as f:
        f.write(data)
    os.replace(path + ".tmp", path)
    st = status(pdir, lang)
    if not st["missing"]:
        pid = _pid(pdir)
        busy = any(j["kind"] == "timing_build" and j["project"] == pid and j["params"].get("lang") == lang
                   and j["status"] in ("queued", "running") for j in jobs.list_jobs(500))
        if not busy:
            jobs.enqueue("timing_build", {"project": pid, "lang": lang}, pid, "Dò thời điểm câu %s" % lang.upper())
        progress.set_lang(pdir, lang, "voice", "done")
        inbox.resolve_key(_key(pdir, lang))
    return st
