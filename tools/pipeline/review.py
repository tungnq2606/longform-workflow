#!/usr/bin/env python3
"""Numbered copies of the frames + visuals/export/review.html (notes box per frame) + export/timeline.csv for CapCut-style editors."""
import csv, html, os, shutil
from _common import video_dir

V = video_dir()
vis = os.path.join(V, "visuals")
exp = os.path.join(vis, "export", "images")
os.makedirs(exp, exist_ok=True)
for f in os.listdir(exp):
    os.remove(os.path.join(exp, f))
src_dir = os.path.join(vis, "frames_1440p") if os.path.isdir(os.path.join(vis, "frames_1440p")) else os.path.join(vis, "frames")
rows = list(csv.DictReader(open(os.path.join(vis, "timeline.csv"), encoding="utf-8")))
ts = lambda s: "%d:%05.2f" % (int(s // 60), s % 60)
out = []
for i, r in enumerate(rows, 1):
    st, du = float(r["timeline_start"]), float(r["duration"])
    new = "%03d_%s.png" % (i, r["frame"][:-4])
    shutil.copy(os.path.join(src_dir, r["frame"]), os.path.join(exp, new))
    out.append({"order": i, "file": new, "start": ts(st), "end": ts(st + du), "duration_s": du, "voice": r["voice"], "says": r["says"]})
with open(os.path.join(vis, "export", "timeline.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
total = float(rows[-1]["timeline_start"]) + float(rows[-1]["duration"])
items = "".join(f'''<div class="it"><img src="images/{o['file']}" loading="lazy"><div><b>#{o['order']} &nbsp; {o['start']} → {o['end']}</b> <span class="d">{o['duration_s']} s</span><br><span class="f">{o['file']} · {o['voice']}</span><br><i>“{html.escape(o['says'])}”</i><br><input class="n" placeholder="ghi chú sửa..."></div></div>''' for o in out)
page = f'''<!doctype html><html><head><meta charset="utf-8"><title>Review</title><style>
body{{margin:0;background:#161614;color:#eceae3;font:14px system-ui}}main{{max-width:1300px;margin:0 auto;padding:16px}}
.it{{display:grid;grid-template-columns:560px 1fr;gap:14px;padding:10px 0;border-bottom:1px solid #333}}img{{width:560px;border-radius:6px}}
.d{{color:#f08a4b;font-weight:600}}.f{{color:#9a988f;font-size:12px}}i{{display:block;margin:6px 0}}.n{{width:90%;padding:5px;background:#222;border:1px solid #444;color:#eee;border-radius:4px}}
button{{padding:7px 12px;border-radius:6px;border:1px solid #444;background:#2a2a27;color:#eee;cursor:pointer}}</style></head><body><main>
<h2>{os.path.basename(V)} · {len(out)} frames · {ts(total)}</h2><p class="f">Write notes, press Copy, paste to Claude. Notes are lost on reload.</p>
<button id="cp">Copy notes</button>{items}
<script>document.getElementById('cp').onclick=()=>{{const t=[...document.querySelectorAll('.it')].map(d=>{{const n=d.querySelector('.n').value.trim();return n?d.querySelector('b').textContent.split(' ')[0]+': '+n:null}}).filter(Boolean).join('\\n');navigator.clipboard.writeText(t||'(no notes)');alert('Copied')}};</script></main></body></html>'''
open(os.path.join(vis, "export", "review.html"), "w", encoding="utf-8").write(page)
print(len(out), "frames ->", os.path.join(vis, "export", "review.html"))
