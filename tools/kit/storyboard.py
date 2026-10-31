"""Shared storyboard pieces: the stick figure, voice/sentence alignment, slideshow page.

Video-specific paths come from the video folder passed in (videos/NNN-slug)."""
import json
import os
import re
import struct
import subprocess
import wave

from build_visuals import ACC, ACC_L, GREY, INK, line, poly, rect, txt

GAP = 0.5   # seconds of silence between voice blocks in the edit
CARD = 1.5  # seconds a chapter card is shown (silence)


def figure(x, y, s=1.0, pose="neutral", brows="flat", eyes="center", mouth="flat"):
    """The one stick figure. Head centre (x, y)."""
    P = {
        "neutral": [[(0, 105), (-45, 160), (-70, 215)], [(0, 105), (45, 160), (70, 215)]],
        "wave": [[(0, 105), (-45, 160), (-70, 215)], [(0, 105), (75, 70), (100, -25)]],
        "paper": [[(0, 105), (-45, 160), (-70, 215)], [(0, 105), (60, 155), (95, 150)]],
        "point": [[(0, 105), (-45, 160), (-70, 215)], [(0, 105), (110, 95), (210, 85)]],
        "finger": [[(0, 105), (-45, 160), (-70, 215)], [(0, 105), (75, 120), (95, 20)]],
        "cross": [[(0, 110), (45, 175), (-35, 150)], [(0, 110), (-45, 175), (35, 150)]],
        "lens": [[(0, 105), (-45, 160), (-70, 215)], [(0, 105), (70, 85), (115, 70)]],
        "shrug": [[(0, 105), (-75, 125), (-105, 55)], [(0, 105), (75, 125), (105, 55)]],
        "think": [[(0, 105), (-45, 160), (-70, 215)], [(0, 105), (75, 150), (30, 78)]],
        "present": [[(0, 105), (-45, 160), (-70, 215)], [(0, 105), (85, 140), (165, 115)]],
    }[pose]
    B = {
        "flat": [((-44, -38), (-14, -38)), ((14, -38), (44, -38))],
        "raise": [((-44, -38), (-14, -38)), ((14, -36), (44, -58))],
        "both": [((-44, -50), (-14, -56)), ((14, -56), (44, -50))],
        "skeptic": [((-44, -44), (-14, -34)), ((14, -34), (44, -44))],
        "worry": [((-44, -34), (-14, -46)), ((14, -46), (44, -34))],
        "low": [((-44, -30), (-14, -30)), ((14, -30), (44, -30))],
    }[brows]
    E = {"center": (0, 0), "left": (-9, 0), "right": (9, 0), "down": (0, 7), "up": (0, -6), "wide": (0, 0)}[eyes]
    M = {
        "flat": [(-18, 34), (18, 34)],
        "smile": [(-20, 28), (0, 38), (20, 28)],
        "smirk": [(-18, 36), (8, 34), (22, 24)],
        "frown": [(-20, 40), (0, 32), (20, 40)],
        "o": None,
    }[mouth]
    g = [f'<g transform="translate({x},{y}) scale({s})">']
    g.append(f'<circle cx="0" cy="0" r="72" fill="#fff" stroke="{INK}" stroke-width="7"/>')
    for ex in (-24, 24):
        if eyes == "wide":
            g.append(f'<circle cx="{ex}" cy="-6" r="13" fill="#fff" stroke="{INK}" stroke-width="4"/>')
        g.append(f'<circle cx="{ex + E[0]}" cy="{-6 + E[1]}" r="6" fill="{INK}"/>')
    for a, b in B:
        g.append(line(a[0], a[1], b[0], b[1], 7))
    if M is None:
        g.append(f'<ellipse cx="0" cy="34" rx="9" ry="11" fill="none" stroke="{INK}" stroke-width="6"/>')
    else:
        g.append(poly(M, w=6))
    g.append(line(0, 72, 0, 235, 7))
    for arm in P:
        g.append(poly(arm, w=7))
    g.append(line(0, 235, -55, 340, 7) + line(0, 235, 55, 340, 7))
    if pose == "paper":
        g.append(rect(60, 70, 100, 130, "#fff", INK, 5, 6))
        g.append(line(76, 100, 144, 100, 4) + line(76, 124, 144, 124, 4) + line(76, 148, 120, 148, 4))
    if pose == "lens":
        g.append(f'<circle cx="140" cy="40" r="42" fill="none" stroke="{INK}" stroke-width="7"/>')
    if pose == "finger":
        g.append(line(95, 20, 95, -12, 7))
    if pose == "shrug":
        g.append(line(-105, 55, -125, 45, 6) + line(105, 55, 125, 45, 6))
    g.append("</g>")
    return "\n".join(g)


def pauses(wav, thr_ratio=0.06, min_ms=150):
    w = wave.open(wav)
    n, sr = w.getnframes(), w.getframerate()
    data = struct.unpack("<%dh" % n, w.readframes(n))
    win = int(sr * 0.01)
    rms = [(sum(x * x for x in data[i:i + win]) / win) ** 0.5 for i in range(0, n - win, win)]
    thr = sorted(rms)[int(len(rms) * 0.95)] * thr_ratio
    out, start = [], None
    for i, r in enumerate(rms):
        if r < thr:
            start = i if start is None else start
        else:
            if start is not None and (i - start) * 10 >= min_ms:
                out.append((start / 100, i / 100))
            start = None
    return out, n / sr


def sentence_starts(video_dir, num):
    text = open(os.path.join(video_dir, "script", "voiceover_tts", "%02d.txt" % num), encoding="utf-8").read().strip()
    sents = re.split(r'(?<=[.!?])\s+(?=[A-Z"])', text)
    wav = os.path.join(video_dir, "visuals", "work", "%02d.wav" % num)
    mp3 = os.path.join(video_dir, "audio", "%02d.mp3" % num)
    if os.path.exists(wav) and os.path.getmtime(wav) < os.path.getmtime(mp3):
        os.remove(wav)  # voice file was re-generated: redo the pause analysis
    if not os.path.exists(wav):
        os.makedirs(os.path.dirname(wav), exist_ok=True)
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", os.path.join(video_dir, "audio", "%02d.mp3" % num), wav], check=True)
    ps, dur = pauses(wav)
    # Global alignment (dynamic programming): pick one pause after each sentence so that
    # sentence lengths in seconds track their text length, favouring longer pauses.
    # A greedy nearest-pause search drifted by one sentence when a comma pause sat
    # close to the expected boundary.
    L = [len(x) for x in sents]
    n = len(L)
    rate = sum(L) / (dur * 0.85)  # characters per second of speech
    exp_ = [max(l / rate, 0.4) for l in L]
    INF = float("inf")
    m = len(ps)
    cost = [[INF] * m for _ in range(n)]
    back = [[-1] * m for _ in range(n)]

    def seg(i, start, end):
        d = end - start
        return (d - exp_[i]) ** 2 / exp_[i] if d > 0.2 else INF

    for j, (pa, pb) in enumerate(ps):
        cost[0][j] = seg(0, 0.0, pa) - 2.0 * (pb - pa)
    for i in range(1, n - 1):
        for j, (pa, pb) in enumerate(ps):
            best, arg = INF, -1
            for k in range(j):
                if cost[i - 1][k] == INF:
                    continue
                c = cost[i - 1][k] + seg(i, ps[k][1], pa)
                if c < best:
                    best, arg = c, k
            if arg >= 0:
                cost[i][j] = best - 2.0 * (pb - pa)
                back[i][j] = arg
    starts = [0.0]
    if n > 1 and m >= n - 1:
        best, arg = INF, -1
        for k in range(m):
            if cost[n - 2][k] == INF:
                continue
            c = cost[n - 2][k] + seg(n - 1, ps[k][1], dur)
            if c < best:
                best, arg = c, k
        chain = []
        i, j = n - 2, arg
        while i >= 0 and j >= 0:
            chain.append(j)
            j = back[i][j]
            i -= 1
        chain.reverse()
        starts += [ps[j][1] - 0.05 for j in chain]
    else:  # not enough pauses: fall back to text proportion
        c = 0
        for l in L[:-1]:
            c += l
            starts.append(c / sum(L) * dur)
    return sents, starts, dur


def write_slideshow(seq, out_dir):
    html = """<!doctype html><html><head><meta charset="utf-8"><title>Video 1 slideshow</title>
<style>body{margin:0;background:#111;color:#ddd;font:14px system-ui}main{max-width:1200px;margin:0 auto;padding:14px}
#st{width:100%;aspect-ratio:16/9;background:#000;border-radius:8px;overflow:hidden}#st img{width:100%;height:100%;object-fit:contain}
.bar{display:flex;gap:8px;align-items:center;margin:10px 0}button,select{padding:7px 12px;border-radius:6px;border:1px solid #444;background:#2a2a27;color:#eee;cursor:pointer;font:inherit}
#info{color:#9a988f;flex:1}</style></head><body><main>
<div id="st"><img id="big"></div>
<div class="bar"><button id="play">Play</button><select id="from"></select><span id="info"></span></div>
<p style="color:#888">Slideshow preview: frames switch at the timings in timeline.csv while your voice files play (../tts/NN.mp3). Hard cuts only; add motion in CapCut.</p>
</main><script>
const seq=__SEQ__;
const big=document.getElementById('big'),info=document.getElementById('info'),sel=document.getElementById('from');
for(let v=1;v<=10;v++){const o=document.createElement('option');o.value=v;o.textContent='Start at voice '+String(v).padStart(2,'0');sel.appendChild(o)}
let audio=null,playing=false,raf=null;
function show(f){big.src='frames/'+f+'.png';info.textContent=f}
function stop(){playing=false;if(audio)audio.pause();cancelAnimationFrame(raf);document.getElementById('play').textContent='Play'}
function playVoice(v){
  if(v>10){stop();return}
  const card=seq.find(s=>s.voice===v&&s.t<0);
  if(card&&!playVoice.cardDone){show(card.frame);playVoice.cardDone=true;setTimeout(()=>{if(playing)playVoice(v)},1500);return}
  playVoice.cardDone=false;
  const beats=seq.filter(s=>s.voice===v&&s.t>=0);show(beats[0].frame);
  audio=new Audio('../audio/'+String(v).padStart(2,'0')+'.mp3');
  const tick=()=>{if(!playing)return;let cur=beats[0];for(const b of beats)if(audio.currentTime>=b.t)cur=b;if(!big.src.endsWith(cur.frame+'.png'))show(cur.frame);raf=requestAnimationFrame(tick)};
  audio.onended=()=>{cancelAnimationFrame(raf);const next=seq.some(s=>s.voice===v+1&&s.t<0);if(playing)setTimeout(()=>playVoice(v+1),next?0:500)};
  audio.play().then(()=>{raf=requestAnimationFrame(tick)}).catch(()=>{info.textContent='Press Play again (autoplay blocked)';stop()});
}
document.getElementById('play').onclick=()=>{if(playing){stop();return}playing=true;document.getElementById('play').textContent='Stop';playVoice(Number(sel.value))};
show(seq[0].frame);
</script></body></html>"""
    open(os.path.join(out_dir, "slideshow.html"), "w", encoding="utf-8").write(html.replace("__SEQ__", json.dumps(seq)))
