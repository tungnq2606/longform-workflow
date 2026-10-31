#!/usr/bin/env python3
"""visuals/timeline.csv -> render/project.json (+1440p), render/subtitles.srt, render/editor.html,
and the 'Chapters:' block of upload/description.txt and upload/upload.txt (names from scenes.DESC_CHAPTERS)."""
import csv, importlib.util, json, os, re, shutil
from _common import TOOLS, video_dir

V = video_dir()
slug = os.path.basename(V)
rows = list(csv.DictReader(open(os.path.join(V, "visuals", "timeline.csv"), encoding="utf-8")))
rd = os.path.join(V, "render")
os.makedirs(rd, exist_ok=True)
clips, audio = [], []
for i, r in enumerate(rows):
    st, du, card = float(r["timeline_start"]), float(r["duration"]), r["voice"] == "(silence)"
    clips.append({"image": "../visuals/frames/" + r["frame"], "start": round(st, 3), "duration": round(du, 3),
                  "zoom": "none" if card else ("in" if i % 2 == 0 else "out"), "fade": 0.4 if card else 0.25, "says": r["says"]})
    if not card and float(r["start_in_voice"]) == 0:
        audio.append({"file": "../audio/" + r["voice"], "start": round(st, 3), "volume": 1.0})
old = os.path.join(rd, "project.json")
music = json.load(open(old)).get("music") if os.path.exists(old) else None  # keep a music choice made in the editor
# Channel standard is 1440p: project.json renders 2560x1440 from visuals/frames_1440p/.
# project_1080p.json is kept for an optional 1080p render (needs frames.py --width 1920).
p1080 = {"width": 1920, "height": 1080, "fps": 30, "clips": clips, "audio": audio, "music": music, "output": slug + "_1080p.mp4"}
json.dump(p1080, open(os.path.join(rd, "project_1080p.json"), "w"), indent=1)
proj = json.loads(json.dumps(p1080))
proj["width"], proj["height"], proj["output"] = 2560, 1440, slug + "_1440p.mp4"
for c in proj["clips"]:
    c["image"] = c["image"].replace("/frames/", "/frames_1440p/")
json.dump(proj, open(old, "w"), indent=1)
open(os.path.join(rd, "project.js"), "w").write("var PROJECT = " + json.dumps(proj) + ";")
shutil.copy(os.path.join(TOOLS, "editor", "editor.html"), os.path.join(rd, "editor.html"))

# subtitles: full sentences (TTS spellings undone)
pron_path = os.path.join(V, "script", "pronounce.json")
undo = {v: k for k, v in json.load(open(pron_path)).items()} if os.path.exists(pron_path) else {}
def ts(s):
    ms = int(round(s * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); sec, ms = divmod(ms, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, sec, ms)
sents = {}
for f in sorted(os.listdir(os.path.join(V, "script", "voiceover_tts"))):
    t = open(os.path.join(V, "script", "voiceover_tts", f), encoding="utf-8").read().strip()
    for a, b in undo.items():
        t = t.replace(a, b)
    sents[f[:2] + ".mp3"] = re.split(r'(?<=[.!?])\s+(?=[A-Z"])', t)
cues = []
for r in rows:
    if r["voice"] == "(silence)":
        continue
    pre = r["says"].strip()
    for a, b in undo.items():
        pre = pre.replace(a, b)
    full = next((x for x in sents.get(r["voice"], []) if x.startswith(pre[:40])), r["says"])
    st, du = float(r["timeline_start"]), float(r["duration"])
    cues.append("%d\n%s --> %s\n%s\n" % (len(cues) + 1, ts(st), ts(st + max(du - 0.05, 0.5)), full))
open(os.path.join(rd, "subtitles.srt"), "w", encoding="utf-8").write("\n".join(cues))

# chapters into the upload texts
spec = importlib.util.spec_from_file_location("scenes", os.path.join(V, "visuals", "scenes.py"))
import sys; sys.path.insert(0, os.path.join(TOOLS, "kit"))
sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)
names = getattr(sc, "DESC_CHAPTERS", {})
first = {}
for r in rows:
    n = int(r["frame"][:2])
    if n in names and n not in first:
        first[n] = float(r["timeline_start"])
chap = "\n".join("%d:%02d %s" % (int(first[n] // 60), int(first[n] % 60), names[n]) for n in sorted(first))
for fn in ("description.txt", "upload.txt"):
    p = os.path.join(V, "upload", fn)
    if os.path.exists(p) and chap:
        s = open(p, encoding="utf-8").read()
        s = re.sub(r"Chapters[^\n]*:\n.*?\n\n", "Chapters:\n" + chap + "\n\n", s, count=1, flags=re.S)
        open(p, "w", encoding="utf-8").write(s)
print("%d clips, %d voice files; chapters:\n%s" % (len(clips), len(audio), chap))
