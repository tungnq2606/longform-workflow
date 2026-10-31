"""Voice timing per language: when each sentence and each beat starts, found from pauses in the owner's mp3 parts.

  lang/<code>/audio/parts.json   [{"part": "01", "file": "01.mp3", "sentences": ["s001", ...]}]   (Plan 6 writes it)
  lang/<code>/timing.json        {"lang", "duration", "beats": [{"id", "start", "end", "sentences": [{"id", "start", "end"}]}],
                                  "parts": [{"part", "start", "duration", "approx"}]}

  python -m tools.longform.timing <project_id> <lang>          (Studio job kind timing_build, lane cpu)

Parts are placed one after another with GAP seconds of silence. Inside a part, the len(sentences)-1 longest pauses
are the sentence boundaries; with too few pauses (a fast speaker) the part is split by character count and marked
approx. mp3 files are decoded with Remotion's bundled ffmpeg (no new system dependency).
"""
import json
import os
import struct
import subprocess
import sys
import wave

from tools.longform import claude_box, jobs, paths, progress, project

ANIM = os.path.join(paths.WS, "tools", "anim")
PY = os.path.join(paths.WS, ".venv", "bin", "python")
GAP = 0.4
EDGE = 0.05  # a pause this close to the start or end of a part is leading/trailing silence, not a boundary


def decode(mp3, wav):
    p = subprocess.run(["npx", "remotion", "ffmpeg", "-y", "-i", os.path.abspath(mp3), "-ac", "1", "-ar", "16000",
                        os.path.abspath(wav)], cwd=ANIM, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0 or not os.path.isfile(wav):
        raise RuntimeError("không giải mã được %s: %s" % (os.path.basename(mp3), (p.stderr or "")[-300:]))


def pauses(wav, thr_ratio=0.06, min_ms=150):
    """Silent stretches [(start, end)] in seconds, and the duration. Port of tools/kit/storyboard.py pauses (stdlib
    wave, 10 ms RMS windows, threshold = thr_ratio x the 95th-percentile window); a trailing silence is kept too."""
    with wave.open(wav) as w:
        n, sr, ch = w.getnframes(), w.getframerate(), w.getnchannels()
        data = struct.unpack("<%dh" % (n * ch), w.readframes(n))[::ch]
    win = max(1, int(sr * 0.01))
    rms = [(sum(x * x for x in data[i:i + win]) / win) ** 0.5 for i in range(0, n - win + 1, win)]
    if not rms:
        return [], n / sr
    thr = sorted(rms)[int(len(rms) * 0.95)] * thr_ratio
    out, start = [], None
    for i, r in enumerate(rms):
        if r < thr:
            start = i if start is None else start
        else:
            if start is not None and (i - start) * 10 >= min_ms:
                out.append((start / 100, i / 100))
            start = None
    if start is not None and (len(rms) - start) * 10 >= min_ms:
        out.append((start / 100, n / sr))
    return out, n / sr


def split_part(pauses, duration, sentences):
    """sentences: [(id, text)] in spoken order -> [{"id", "start", "end", "approx"}] in seconds from the part start."""
    lo, hi = 0.0, duration
    inner = []
    for a, b in pauses:
        if a <= EDGE:
            lo = max(lo, b)
        elif b >= duration - EDGE:
            hi = min(hi, a)
        else:
            inner.append((a, b))
    need = len(sentences) - 1
    if len(inner) >= need:
        cuts = sorted(sorted(inner, key=lambda p: p[1] - p[0], reverse=True)[:need])
        starts = [lo] + [b for _, b in cuts]
        ends = [a for a, _ in cuts] + [hi]
        approx = False
    else:
        weights = [max(1, len(t or "")) for _, t in sentences]
        total, acc, bounds = float(sum(weights)), 0, [lo]
        for w in weights:
            acc += w
            bounds.append(lo + (hi - lo) * acc / total)
        starts, ends = bounds[:-1], bounds[1:]
        approx = True
    return [{"id": sid, "start": round(s, 3), "end": round(e, 3), "approx": approx}
            for (sid, _), s, e in zip(sentences, starts, ends)]


def _audio(pdir, lang):
    return os.path.join(pdir, "lang", lang, "audio")


def load_parts(pdir, lang):
    try:
        with open(os.path.join(_audio(pdir, lang), "parts.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def missing_parts(pdir, lang):
    """Part names in parts.json whose mp3 is not there yet (empty when no parts are prepared)."""
    return [p["part"] for p in load_parts(pdir, lang) or [] if not os.path.isfile(os.path.join(_audio(pdir, lang), p["file"]))]


def lang_script(pdir, lang):
    """The script of one language: lang/<code>/script/script.json, or script/script.json for the source language."""
    src = project.load_project(pdir).get("source_lang", project.SOURCE_LANG)
    p = os.path.join(pdir, "script", "script.json") if lang == src else os.path.join(pdir, "lang", lang, "script", "script.json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def load(pdir, lang):
    try:
        with open(os.path.join(pdir, "lang", lang, "timing.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def build(pdir, lang):
    parts = load_parts(pdir, lang)
    if not parts:
        raise ValueError("chưa có danh sách phần giọng (%s)" % lang)
    missing = missing_parts(pdir, lang)
    if missing:
        raise ValueError("thiếu giọng phần %s" % ", ".join(missing))
    doc = lang_script(pdir, lang)
    if not doc:
        raise ValueError("chưa có kịch bản %s" % lang)
    text, beat_of, order = {}, {}, []
    for ch in doc.get("chapters", []):
        for b in ch.get("beats", []):
            order.append(b["id"])
            for s in b.get("sentences", []):
                text[s["id"]], beat_of[s["id"]] = s.get("text", ""), b["id"]
    sentences, part_rows, t = [], [], 0.0
    for p in parts:
        unknown = [s for s in p["sentences"] if s not in text]
        if unknown:
            raise ValueError("phần %s có câu không có trong kịch bản %s: %s" % (p["part"], lang, ", ".join(unknown)))
        wav = os.path.join(_audio(pdir, lang), "work", os.path.splitext(p["file"])[0] + ".wav")
        mp3 = os.path.join(_audio(pdir, lang), p["file"])
        if not os.path.isfile(wav) or os.path.getmtime(wav) < os.path.getmtime(mp3):
            os.makedirs(os.path.dirname(wav), exist_ok=True)
            decode(mp3, wav)
        ps, dur = pauses(wav)
        rows = split_part(ps, dur, [(s, text[s]) for s in p["sentences"]])
        approx = any(r["approx"] for r in rows)
        for r in rows:
            sentences.append({"id": r["id"], "start": round(t + r["start"], 3), "end": round(t + r["end"], 3)})
        part_rows.append({"part": p["part"], "start": round(t, 3), "duration": round(dur, 3), "approx": approx})
        t += dur + GAP
    beats = {}
    for s in sentences:
        beats.setdefault(beat_of[s["id"]], []).append(s)
    out = {"lang": lang, "duration": round(t - GAP, 3) if parts else 0.0,
           "beats": [{"id": b, "start": beats[b][0]["start"], "end": beats[b][-1]["end"], "sentences": beats[b]}
                     for b in order if b in beats],
           "parts": part_rows}
    path = os.path.join(pdir, "lang", lang, "timing.json")
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    os.replace(path + ".tmp", path)
    progress.set_lang(pdir, lang, "voice", "done")
    return out


def _job_argv(params):
    pid = claude_box.check_project(params.get("project"))
    if pid is None:
        raise ValueError("thiếu dự án")
    lang = params.get("lang")
    if lang not in project.load_project(os.path.join(paths.projects(), pid))["languages"]:
        raise ValueError("dự án không có ngôn ngữ %s" % lang)
    return [PY, "-m", "tools.longform.timing", pid, lang]


jobs.register(jobs.Kind("timing_build", "cpu", _job_argv))


def main(argv):
    pid, lang = argv
    if claude_box.check_project(pid) is None:
        print("lỗi: không có dự án %s" % pid)
        return 1
    try:
        out = build(os.path.join(paths.projects(), pid), lang)
    except (ValueError, RuntimeError) as e:
        print("lỗi: %s" % e, flush=True)
        return 1
    approx = [p["part"] for p in out["parts"] if p["approx"]]
    print("ok: %d cảnh, %.1f giây%s" % (len(out["beats"]), out["duration"],
                                       ("; phần ước lượng theo số chữ: %s" % ", ".join(approx)) if approx else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
