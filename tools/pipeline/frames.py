#!/usr/bin/env python3
"""Draw every frame of a video and time it to the voice.

Usage: frames.py videos/NNN-slug [--width 1920] [--only N]   (default 2560x1440, channel standard)
Reads visuals/scenes.py (S, BG, CHAPTERS), script/voiceover_tts/*.txt and audio/*.mp3.
Writes visuals/frames_1440p/ (or frames/ for --width 1920), visuals/timeline.csv, visuals/slideshow.html.
"""
import csv, importlib.util, os, sys
from _common import video_dir

V = video_dir()
width = int(sys.argv[sys.argv.index("--width") + 1]) if "--width" in sys.argv else 2560  # channel standard: 1440p
only = int(sys.argv[sys.argv.index("--only") + 1]) if "--only" in sys.argv else None
os.environ["OUT_W"] = str(width)
import build_visuals as bv  # noqa: E402
import scene_kit as kit  # noqa: E402
from storyboard import CARD, GAP, sentence_starts, write_slideshow  # noqa: E402

spec = importlib.util.spec_from_file_location("scenes", os.path.join(V, "visuals", "scenes.py"))
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)
S, BG, CHAPTERS = sc.S, sc.BG, getattr(sc, "CHAPTERS", {})

vis = os.path.join(V, "visuals")
fdir = os.path.join(vis, "frames" if width == 1920 else "frames_%dp" % (width * 9 // 16))
hdir = os.path.join(vis, "work", "html")
os.makedirs(fdir, exist_ok=True)
os.makedirs(hdir, exist_ok=True)
if only is None:
    for f in os.listdir(fdir):
        if f.endswith(".png"):
            os.remove(os.path.join(fdir, f))
blocks = sorted(S)
rows, seq, abs_t = [], [], 0.0
for num in blocks:
    beats = S[num]
    sents, starts, dur = sentence_starts(V, num)
    if num in CHAPTERS:
        name = "%02d_00_card" % num
        hp = os.path.join(hdir, name + ".html")
        open(hp, "w", encoding="utf-8").write(kit.page(kit.card_scene(num, CHAPTERS), BG[num], 900 + num))
        if only in (None, num):
            bv.render(hp, os.path.join(fdir, name + ".png"), width, width * 9 // 16)
        rows.append({"voice": "(silence)", "frame": name + ".png", "start_in_voice": 0, "duration": CARD,
                     "timeline_start": round(abs_t, 2), "says": "Part: " + CHAPTERS[num]})
        seq.append({"voice": num, "frame": name, "t": -1})
        abs_t += CARD
    gap_after = 0 if (num + 1) in CHAPTERS or num == blocks[-1] else GAP
    times = []
    for si, frac, _ in beats:
        s0 = starts[si - 1]
        s1 = starts[si] if si < len(starts) else dur
        times.append(s0 + frac * (s1 - s0))
    times[0] = 0.0
    for k, (si, frac, body) in enumerate(beats):
        name = "%02d_%02d" % (num, k + 1)
        hp = os.path.join(hdir, name + ".html")
        open(hp, "w", encoding="utf-8").write(kit.page(body, BG[num], num * 10 + k))
        if only in (None, num):
            bv.render(hp, os.path.join(fdir, name + ".png"), width, width * 9 // 16)
        t0 = times[k]
        t1 = times[k + 1] if k + 1 < len(times) else dur
        rows.append({"voice": "%02d.mp3" % num, "frame": name + ".png", "start_in_voice": round(t0, 2),
                     "duration": round(t1 - t0 + (gap_after if k + 1 == len(times) else 0), 2),
                     "timeline_start": round(abs_t + t0, 2), "says": sents[si - 1][:80]})
        seq.append({"voice": num, "frame": name, "t": round(t0, 2)})
    abs_t += dur + gap_after
with open(os.path.join(vis, "timeline.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
write_slideshow(seq, vis)
print("frames: %d (%s), total %.1f s" % (len(rows), os.path.basename(fdir), abs_t))
