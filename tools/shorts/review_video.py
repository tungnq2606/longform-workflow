#!/usr/bin/env python3
"""Automatic Gemini + FFmpeg review for 9:16 Shorts Veo clips and rendered videos.

Modes:
  review_video.py VIDEO_DIR --clips [--only S01,S06A] [--all] [--workers 2]
      Extracts a 6-frame timestamped contact sheet + FFmpeg motion/seam-jolt metrics for each
      Veo clip in VIDEO_DIR/clips/<ID>.mp4 and reviews with Gemini against vn-ligne-claire style,
      source keyframe, and veo_prompt. Writes VIDEO_DIR/images/runs/clip_review.json.

  review_video.py VIDEO_DIR --render [--file render/final_youtube_4k.mp4]
      Aligns the rendered 9:16 MP4 against all script blocks, checks LUFS/peak/silence audio health
      and visual-to-narration sync across 20 timestamped frames with Gemini.
      Writes VIDEO_DIR/render/review.json.
"""
import fcntl
import html as H
import json
import math
import os
import re
import struct
import subprocess
import sys
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(os.path.dirname(HERE))
KIT = os.path.join(WS, "tools", "kit")
FONTS = os.path.join(KIT, "fonts")
if KIT not in sys.path:
    sys.path.insert(0, KIT)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import build_visuals as bv  # noqa: E402
from render_shorts import FFMPEG, ff_env, detect_block_marks  # noqa: E402

AGY = os.path.expanduser("~/.local/bin/agy")
MODEL = "gemini-4-argon-high"
CLIP_BATCH = 2

CLIP_SCHEMA = {
    "type": "object",
    "properties": {
        "reviews": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "ok": {"type": "boolean"},
                    "score": {"type": "integer", "minimum": 1, "maximum": 5},
                    "problems": {"type": "array", "items": {"type": "string"}},
                    "fix": {
                        "type": "string",
                        "description": "improved English Veo motion prompt if the clip should be regenerated on Google Flow; empty string if ok",
                    },
                    "trim_out_sec": {
                        "type": "number",
                        "description": "if early frames are good but the clip morphs/breaks near the tail after T seconds, set T (e.g. 5.2); otherwise 0",
                    },
                },
                "required": ["id", "ok", "score", "problems", "fix", "trim_out_sec"],
            },
        }
    },
    "required": ["reviews"],
}

RENDER_SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean"},
        "score": {"type": "integer", "minimum": 1, "maximum": 5},
        "summary": {"type": "string"},
        "audio_verdict": {"type": "string"},
        "pacing_verdict": {"type": "string"},
        "recommend_smooth_jolts": {"type": "boolean"},
        "problems": {"type": "array", "items": {"type": "string"}},
        "fixes": {"type": "array", "items": {"type": "string"}},
        "blocks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "block": {"type": "integer"},
                    "ok": {"type": "boolean"},
                    "note": {"type": "string"},
                },
                "required": ["block", "ok", "note"],
            },
        },
    },
    "required": [
        "ok",
        "score",
        "summary",
        "audio_verdict",
        "pacing_verdict",
        "recommend_smooth_jolts",
        "problems",
        "fixes",
        "blocks",
    ],
}

CLIP_RUBRIC = """You are reviewing Veo 3.1 vertical 9:16 video clips for the Vietnamese history Shorts channel "Công Trường Lịch Sử" (2D hand-drawn ink & muted watercolor ligne-claire style).
For each clip, inspect its 6-frame timestamped contact sheet (frames #1..#6 from start to end of the clip) and compare against the Approved Channel Style Reference and (if listed) its Source First-Frame PNG.

LANGUAGE RULE:
- Write `problems` in concise, natural VIETNAMESE (for the Vietnamese producer).
- Write `fix` in concise ENGLISH as a complete ready-to-paste Veo motion prompt if the clip should be regenerated (or empty string "" if `ok` is true).

Check for real Veo defects ONLY if visible in the contact sheet or metrics:
1. Style Drift Across Time: Frame #1 to #6 must stay 2D hand-drawn dark-brown ink outlines & muted earth-tone watercolor. Flag if mid-clip frames drift into 3D CGI, photorealistic video, blurry smear, or melted faces/limbs.
2. Veo Morphing & Physics Glitches: Flag if boats, wooden stakes, or walls pop/grow out of nowhere by magic instead of physical movement; people walking on top of water instead of standing on boats/rafts or wading; river water turning into a brown mud road; or sudden camera spin on a static/ambient shot.
3. Motion Mode & Action Fit:
   - `ambient`: camera steady, gentle water ripples / wind / mist / torchlight without distorting buildings or characters.
   - `active`: clear, readable physical action matching `veo_prompt` and `vo` (e.g. driving stakes, warship impaling on stakes, archers shooting).
4. Tail Breakdown vs Full Redo (`trim_out_sec`):
   - If frames #1–#4 (e.g. first 4.5–5.5s) look clean and match the required shot `needed_duration`, and ONLY frame #5 or #6 near the end morphs/breaks, set `trim_out_sec` to the last clean second (e.g. `5.2`), note it in `problems`, and give `score = 4` (`ok = true`) if `trim_out_sec >= needed_duration`, or `score = 3` (`ok = false`) if the break happens earlier than `needed_duration`.
   - Otherwise set `trim_out_sec = 0`.
5. No Text / No Subtitles / No UI: Flag any random letters, watermarks, or UI overlays generated by Veo.
Score 5 = clean ready-to-cut clip, 4 = usable (minor flaw or clean after `trim_out_sec`), 3 or less = regenerate on Google Flow. `ok = score >= 4`."""

RENDER_RUBRIC = """You are the lead post-production reviewer for the Vietnamese YouTube Shorts & TikTok history channel "Công Trường Lịch Sử" (1080x1920 vertical 9:16, ~80-95s, 2D hand-drawn ink & muted watercolor ligne-claire style).
Inspect the two timestamped storyboard contact-sheet grids covering all narration blocks [1]..[N], together with the full Vietnamese script, block timestamps, and FFmpeg audio/jolt diagnostics.

Write ALL output fields (`summary`, `audio_verdict`, `pacing_verdict`, `problems`, `fixes`, and `blocks[].note`) in natural, concise VIETNAMESE.

Evaluate:
1. Opening Hook (first 2.5s of Block [1]): Does the very first tile grab attention immediately with clear high-contrast action/scale on a phone screen?
2. Visual-to-Voiceover Sync Across Blocks [1]..[N]: Does each block's pair of frames match what the narrator is speaking in that block? Flag if any block appears shifted/desynced (showing the previous or next beat's visuals), repeats stuck frames awkwardly, or misses the archaeological payoff in the final block.
3. Visual & Aspect Consistency: Strict 9:16 full-bleed vertical framing (no black letterbox/pillarbox bars), consistent 2D ligne-claire art across cuts, zero unintended text/watermarks.
4. Audio & Pacing Health: Check integrated loudness (ideal Shorts voice + light BGM is roughly -19 to -13 LUFS, true peak <= -0.3 dBTP), flag any jarring mid-sentence dead air (>1.3s silence), clipping, or missing audio. If FFmpeg detected multiple Veo chunk-seam jolts (around clip frames 64/128), set `recommend_smooth_jolts = true` and suggest ticking "Khử giật seam Veo (frame 64/128)" when re-rendering.
Score 5 = ready to publish on YouTube Shorts & TikTok, 4 = good draft with minor polish optional, 3 or less = fix issues and re-render. `ok = score >= 4`."""


def probe_media(path):
    out = subprocess.run([FFMPEG, "-hide_banner", "-i", path], capture_output=True, text=True, env=ff_env()).stderr
    m_dur = re.search(r"Duration:\s*(\d+):(\d+):([0-9.]+)", out)
    dur = (int(m_dur.group(1)) * 3600 + int(m_dur.group(2)) * 60 + float(m_dur.group(3))) if m_dur else 0.0
    m_sz = re.search(r"Video:.*?,\s*(\d{2,5})x(\d{2,5})", out)
    w, h = (int(m_sz.group(1)), int(m_sz.group(2))) if m_sz else (0, 0)
    m_fps = re.search(r"([0-9.]+)\s*fps", out)
    fps = float(m_fps.group(1)) if m_fps else 24.0
    has_audio = "Audio:" in out
    return {"duration": dur, "width": w, "height": h, "fps": fps, "has_audio": has_audio}


def analyze_motion_jolts(path, fps=24.0, max_sec=None):
    cmd = [FFMPEG, "-v", "error"]
    if max_sec:
        cmd += ["-t", f"{max_sec:.2f}"]
    cmd += ["-i", path, "-an", "-vf", "scale=72:128,format=gray", "-f", "image2pipe", "-c:v", "rawvideo", "-"]
    p = subprocess.run(cmd, capture_output=True, env=ff_env())
    raw = p.stdout
    fsz = 72 * 128
    nf = len(raw) // fsz
    if nf < 4:
        return {"frames": nf, "median_diff": 0.0, "seam_jolts": [], "jumps": []}

    diffs = [0.0]
    for i in range(1, nf):
        a = raw[(i - 1) * fsz:i * fsz]
        b = raw[i * fsz:(i + 1) * fsz]
        diffs.append(sum(abs(x - y) for x, y in zip(a, b)) / float(fsz))

    s_all = sorted(diffs[1:])
    g_med = s_all[len(s_all) // 2] if s_all else 0.2

    seam_jolts = []
    for target in (64, 128, 192):
        if target >= nf - 2:
            continue
        win = [diffs[k] for k in range(max(1, target - 10), min(nf, target + 11)) if abs(k - target) > 1]
        if not win:
            continue
        l_med = sorted(win)[len(win) // 2]
        best_f = max((target - 1, target, target + 1), key=lambda k: diffs[k] if 1 <= k < nf else 0.0)
        val = diffs[best_f]
        if val > max(l_med * 1.9, l_med + 0.95):
            seam_jolts.append({
                "frame": best_f,
                "sec": round(best_f / fps, 2),
                "ratio": round(val / max(l_med, 0.15), 1),
            })

    jumps = []
    last_j = -10
    for i in range(2, nf):
        if diffs[i] > max(g_med * 3.6, 5.0) and i - last_j >= 6:
            jumps.append({"frame": i, "sec": round(i / fps, 2), "diff": round(diffs[i], 2)})
            last_j = i

    return {
        "frames": nf,
        "median_diff": round(g_med, 3),
        "seam_jolts": seam_jolts,
        "jumps": jumps[:15],
    }


def analyze_audio(path, duration):
    info = probe_media(path)
    if not info["has_audio"]:
        return {"has_audio": False, "lufs": None, "true_peak_db": None, "long_silences": []}

    p_ln = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", path, "-vn", "-af", "loudnorm=print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, env=ff_env()
    ).stderr
    lufs, tp = None, None
    jb = p_ln.rfind("{")
    je = p_ln.rfind("}")
    if 0 <= jb < je:
        try:
            ln = json.loads(p_ln[jb:je + 1])
            lufs = round(float(ln.get("input_i", -99)), 1)
            tp = round(float(ln.get("input_tp", -99)), 1)
        except (ValueError, TypeError):
            pass

    p_sil = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", path, "-vn", "-af", "silencedetect=noise=-38dB:d=1.25", "-f", "null", "-"],
        capture_output=True, text=True, env=ff_env()
    ).stderr
    starts = [float(x) for x in re.findall(r"silence_start:\s*([0-9.]+)", p_sil)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([0-9.]+)", p_sil)]
    silences = []
    for s, e in zip(starts, ends):
        if s > 0.2 and e < max(0.5, duration - 1.8):
            silences.append({"start": round(s, 2), "end": round(e, 2), "dur": round(e - s, 2)})
    return {"has_audio": True, "lufs": lufs, "true_peak_db": tp, "long_silences": silences}


def _png_chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def _write_rgb_png(path, w, h, rgb_rows):
    raw = b"".join(b"\x00" + row for row in rgb_rows)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    data = b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", zlib.compress(raw, 6)) + _png_chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(data)


_GLYPHS = {
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E), "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F), "3": (0x1F, 0x02, 0x04, 0x06, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02), "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E), "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E), "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11), "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E), "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F), "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F), "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E), "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11), "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11), "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E), "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D), "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E), "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E), "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11), "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04), "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    ".": (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C), "#": (0x0A, 0x1F, 0x0A, 0x0A, 0x1F, 0x0A, 0x00),
    "[": (0x0E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x0E), "]": (0x0E, 0x02, 0x02, 0x02, 0x02, 0x02, 0x0E),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02), ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "-": (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00), " ": (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
}


def _stamp_tile_badge(buf, tw, th, label):
    """Burn a crisp 2x-scaled ASCII badge onto an rgb24 tile buffer."""
    arr = bytearray(buf)
    txt = "".join(ch if ch in _GLYPHS else ("-" if ch in "·–:" else " ") for ch in label.upper()).strip()
    txt = re.sub(r"\s+", " ", txt)[:22]
    scale = 2
    cw = 6 * scale
    ch_h = 7 * scale
    pad_x, pad_y = 6, 5
    bw = min(tw - 8, len(txt) * cw + pad_x * 2)
    bh = ch_h + pad_y * 2
    x0, y0 = 6, max(4, th - bh - 6)
    for y in range(y0, min(th, y0 + bh)):
        row_off = y * tw * 3
        for x in range(x0, min(tw, x0 + bw)):
            p = row_off + x * 3
            arr[p] = arr[p] // 4 + 12
            arr[p + 1] = arr[p + 1] // 4 + 10
            arr[p + 2] = arr[p + 2] // 4 + 8
    for idx, ch in enumerate(txt):
        gx0 = x0 + pad_x + idx * cw
        if gx0 + 5 * scale >= x0 + bw:
            break
        rows_bits = _GLYPHS.get(ch, _GLYPHS[" "])
        for gy, bits in enumerate(rows_bits):
            for gx in range(5):
                if bits & (1 << (4 - gx)):
                    for dy in range(scale):
                        for dx in range(scale):
                            px = gx0 + gx * scale + dx
                            py = y0 + pad_y + gy * scale + dy
                            if 0 <= px < tw and 0 <= py < th:
                                p = (py * tw + px) * 3
                                arr[p], arr[p + 1], arr[p + 2] = 255, 218, 90
    return bytes(arr)


def _fallback_stitch_png(video_path, stamps, out_png, cols, tile_w, tile_h):
    rows_n = math.ceil(len(stamps) / float(cols))
    pad = 4
    W = cols * tile_w + (cols + 1) * pad
    Hh = rows_n * tile_h + (rows_n + 1) * pad
    bg = b"\x16\x15\x13"
    tiles = []
    vf = f"scale={tile_w}:{tile_h}:force_original_aspect_ratio=increase,crop={tile_w}:{tile_h}"
    need_bytes = tile_w * tile_h * 3
    for sec, label in stamps:
        p = subprocess.run(
            [FFMPEG, "-v", "error", "-ss", f"{max(0.0, sec):.3f}", "-i", video_path, "-frames:v", "1", "-an",
             "-vf", vf, "-pix_fmt", "rgb24", "-f", "image2pipe", "-c:v", "rawvideo", "-"],
            capture_output=True, env=ff_env()
        )
        buf = p.stdout
        if len(buf) < need_bytes:
            buf = buf + (b"\x22\x20\x1d" * tile_w * tile_h)
        tiles.append(_stamp_tile_badge(buf[:need_bytes], tile_w, tile_h, label))

    while len(tiles) < rows_n * cols:
        tiles.append(bg * (tile_w * tile_h))

    rgb_rows = []
    blank_row = bg * W
    for r in range(rows_n):
        for _ in range(pad):
            rgb_rows.append(blank_row)
        row_tiles = tiles[r * cols:(r + 1) * cols]
        for y in range(tile_h):
            parts = [bg * pad]
            for tbuf in row_tiles:
                off = y * tile_w * 3
                parts.append(tbuf[off:off + tile_w * 3])
                parts.append(bg * pad)
            rgb_rows.append(b"".join(parts))
    for _ in range(pad):
        rgb_rows.append(blank_row)
    _write_rgb_png(out_png, W, Hh, rgb_rows)
    return os.path.exists(out_png)


def make_contact_sheet(video_path, stamps, out_png, cols=2, tile_w=340, tile_h=604, header=""):
    """Extract timestamped frames and compose a labeled contact-sheet PNG."""
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    tmp_dir = out_png + "_tiles"
    os.makedirs(tmp_dir, exist_ok=True)
    vf = f"scale={tile_w}:{tile_h}:force_original_aspect_ratio=increase,crop={tile_w}:{tile_h}"
    tile_files = []
    for k, (sec, label) in enumerate(stamps):
        tf = os.path.join(tmp_dir, f"t_{k:02d}.png")
        subprocess.run(
            [FFMPEG, "-y", "-v", "error", "-ss", f"{max(0.0, sec):.3f}", "-i", video_path,
             "-frames:v", "1", "-vf", vf, tf],
            capture_output=True, env=ff_env()
        )
        tile_files.append((tf, label))

    rows_n = math.ceil(len(stamps) / float(cols))
    gap = 10
    head_h = 44 if header else 12
    W = cols * tile_w + (cols + 1) * gap
    Hh = head_h + rows_n * tile_h + rows_n * gap + 6

    cells = []
    for tf, label in tile_files:
        img_tag = f'<img src="file://{tf}">' if os.path.exists(tf) else '<div class="miss">NO FRAME</div>'
        cells.append(f'<div class="cell">{img_tag}<div class="tag">{H.escape(label)}</div></div>')

    head_html = f'<div class="hdr">{H.escape(header)}</div>' if header else ""
    html_doc = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:'BVP';font-weight:700;src:url('file://{FONTS}/BeVietnamPro-Bold.ttf')}}
html,body{{margin:0;width:{W}px;height:{Hh}px;overflow:hidden;background:#161513;color:#f5f2eb;font-family:'BVP',sans-serif}}
.hdr{{height:{head_h}px;display:flex;align-items:center;padding:0 {gap}px;font-size:16px;font-weight:700;color:#ffd23f;box-sizing:border-box}}
.grid{{display:grid;grid-template-columns:repeat({cols},{tile_w}px);gap:{gap}px;padding:0 {gap}px {gap}px}}
.cell{{position:relative;width:{tile_w}px;height:{tile_h}px;border-radius:8px;overflow:hidden;background:#262420;border:1px solid #3a3630}}
.cell img{{width:100%;height:100%;object-fit:cover;display:block}}
.tag{{position:absolute;left:8px;bottom:8px;right:8px;background:rgba(16,14,10,.82);color:#fff;font-size:13px;font-weight:700;padding:4px 8px;border-radius:6px;line-height:1.25}}
.miss{{display:flex;align-items:center;justify-content:center;height:100%;color:#e87c6c;font-size:14px}}
</style></head><body>{head_html}<div class="grid">{"".join(cells)}</div></body></html>"""

    hp = os.path.join(tmp_dir, "sheet.html")
    with open(hp, "w", encoding="utf-8") as fh:
        fh.write(html_doc)
    if os.path.exists(out_png):
        os.remove(out_png)

    ok = bv.render(hp, out_png, W, Hh)
    if not ok or not os.path.exists(out_png):
        ok = _fallback_stitch_png(video_path, stamps, out_png, cols, tile_w, tile_h)

    for fn in os.listdir(tmp_dir):
        try:
            os.remove(os.path.join(tmp_dir, fn))
        except OSError:
            pass
    try:
        os.rmdir(tmp_dir)
    except OSError:
        pass
    return ok


def load_style_ref(style_name="vn-ligne-claire"):
    sp = os.path.join(WS, "tools", "imageprompts", "style", (style_name or "vn-ligne-claire").replace("-", "_") + ".json")
    if os.path.exists(sp):
        obj = json.load(open(sp, encoding="utf-8"))
        for r in obj.get("style_refs", []):
            ap = os.path.abspath(os.path.join(WS, r))
            if os.path.exists(ap):
                return ap
    return None


def run_agy_json(task, schema, work_dir):
    os.makedirs(work_dir, exist_ok=True)
    p = subprocess.run(
        [AGY, "-p", task, "--model", MODEL, "--output-format", "json", "--json-schema", json.dumps(schema),
         "--print-timeout", "900s", "--dangerously-skip-permissions", "--add-dir", WS],
        cwd=work_dir, capture_output=True, text=True, timeout=1200
    )
    res = json.loads(p.stdout[p.stdout.find("{"):])
    body = res.get("structured_output") or res.get("response")
    return body if isinstance(body, dict) else json.loads(body[body.find("{"):body.rfind("}") + 1])


def review_clips(vdir, only=None, review_all=False, workers=2, paths=None):
    """paths: optional {id: clip path} to review a file other than clips/<id>.mp4 (flow_clips.py test clips)."""
    img_dir = os.path.join(vdir, "images")
    clips_dir = os.path.join(vdir, "clips")
    runs_dir = os.path.join(img_dir, "runs")
    strips_dir = os.path.join(runs_dir, "clip_strips")
    os.makedirs(runs_dir, exist_ok=True)

    man_path = os.path.join(img_dir, "prompts", "manifest.json")
    man_doc = json.load(open(man_path, encoding="utf-8")) if os.path.exists(man_path) else {"items": []}
    items = [it for it in man_doc.get("items", []) if it.get("kind") == "scene"]
    if not items and os.path.isdir(clips_dir):
        for idx, fn in enumerate(sorted(os.listdir(clips_dir)), 1):
            if fn.endswith(".mp4"):
                sid = fn[:-4]
                items.append({"seq": idx, "id": sid, "kind": "scene", "duration": 4.5, "motion_mode": "active",
                              "veo_prompt": "", "vo": "", "save_as": f"frames/{sid}.png"})

    rv_path = os.path.join(runs_dir, "clip_review.json")
    reviews = json.load(open(rv_path, encoding="utf-8")) if os.path.exists(rv_path) else {}

    todo = []
    for it in items:
        cp = (paths or {}).get(it["id"]) or os.path.join(clips_dir, it["id"] + ".mp4")
        if not os.path.exists(cp):
            continue
        if only and it["id"] not in only:
            continue
        r = reviews.get(it["id"], {})
        if not only and not review_all and abs(r.get("mtime", 0) - os.path.getmtime(cp)) < 1:
            continue
        todo.append((it, cp))

    if not todo:
        print("Không có clip Veo mới cần kiểm (tất cả clip hiện có đã được kiểm).", flush=True)
        return

    style_ref = load_style_ref(man_doc.get("style", "vn-ligne-claire"))
    print(f"Đang trích xuất dải 6 frame & quét độ giật cho {len(todo)} clip Veo...", flush=True)

    prepared = []
    for it, cp in todo:
        sid = it["id"]
        info = probe_media(cp)
        dur = max(0.5, info["duration"])
        fps = info["fps"] or 24.0
        jolt_info = analyze_motion_jolts(cp, fps=fps)
        fracs = (0.04, 0.22, 0.40, 0.58, 0.76, 0.93)
        stamps = []
        for idx, fr in enumerate(fracs, 1):
            t = min(max(0.05, dur * fr), max(0.05, dur - 0.08))
            stamps.append((t, f"#{idx} · {t:.1f}s (f{int(round(t * fps))})"))
        strip_png = os.path.join(strips_dir, f"{sid}_strip.png")
        hdr = f"Clip {sid}.mp4 · {dur:.1f}s · {info['width']}x{info['height']} · {it.get('motion_mode', 'ambient')}"
        make_contact_sheet(cp, stamps, strip_png, cols=2, tile_w=320, tile_h=568, header=hdr)
        prepared.append((it, cp, info, jolt_info, strip_png))

    batches = [prepared[i:i + CLIP_BATCH] for i in range(0, len(prepared), CLIP_BATCH)]
    print(f"Gửi Gemini kiểm {len(prepared)} clip Veo ({len(batches)} lượt, {workers} luồng song song)...", flush=True)
    lock = threading.Lock()

    def run_batch(batch):
        parts = []
        if style_ref:
            parts.append(f"Approved Channel Style Reference (2D ligne-claire ink & muted watercolor): {style_ref}")
        for it, cp, info, jolt_info, strip_png in batch:
            sid = it["id"]
            src_frame = os.path.join(img_dir, it.get("save_as", ""))
            seam_str = ", ".join(f"frame {j['frame']} ({j['sec']}s, {j['ratio']}x)" for j in jolt_info["seam_jolts"]) or "none"
            jump_str = ", ".join(f"frame {j['frame']} ({j['sec']}s)" for j in jolt_info["jumps"]) or "none"
            lines = [
                f"Clip id {sid}:",
                f"- 6-frame timestamped contact sheet (READ THIS IMAGE): {strip_png}",
            ]
            if os.path.exists(src_frame):
                lines.append(f"- Source First-Frame 9:16 PNG (READ THIS IMAGE for style/layout comparison): {src_frame}")
            lines += [
                f"- Technical: duration={info['duration']:.2f}s, resolution={info['width']}x{info['height']}, fps={info['fps']:.1f}, median_frame_delta={jolt_info['median_diff']}",
                f"- FFmpeg Veo chunk-seam jolts (around frames 64/128): {seam_str}",
                f"- FFmpeg sudden jumps/snaps: {jump_str}",
                f"- Needed timeline duration for this shot: {float(it.get('duration', 4.5)):.1f}s | motion_mode: {it.get('motion_mode', 'ambient')}",
                f"- Voiceover (VO): {it.get('vo', '')}",
                f"- Camera: {it.get('camera', '')}",
                f"- Original Veo motion prompt: {it.get('veo_prompt', '(none)')}",
            ]
            parts.append("\n".join(lines))

        task = (
            "You are a Veo video quality reviewer. Open and inspect EVERY image path listed below using your file viewing tool. "
            "Do not edit, generate or write any files.\n\n"
            f"{CLIP_RUBRIC}\n\n" + "\n\n".join(parts) + "\n\nReturn one review object per clip id."
        )
        t0 = time.time()
        try:
            data = run_agy_json(task, CLIP_SCHEMA, runs_dir)
        except Exception as e:
            print(f"Lượt kiểm clip lỗi ({e})", flush=True)
            return

        got = {r["id"]: r for r in data.get("reviews", [])}
        with lock:
            for it, cp, info, jolt_info, strip_png in batch:
                sid = it["id"]
                r = got.get(sid)
                if not r:
                    print(f"{sid:<8} không nhận được kết quả từ Gemini", flush=True)
                    continue
                r.update(
                    file=os.path.relpath(cp, vdir),
                    strip=os.path.relpath(strip_png, vdir),
                    duration=round(info["duration"], 2),
                    resolution=f"{info['width']}x{info['height']}",
                    seam_jolts=jolt_info["seam_jolts"],
                    jumps=jolt_info["jumps"],
                    mtime=os.path.getmtime(cp),
                    at=time.strftime("%Y-%m-%d %H:%M"),
                )
                reviews[sid] = r
                verdict = "ĐẠT " if r["ok"] else "LÀM LẠI"
                probs = "; ".join(r.get("problems", []))[:160]
                print(f"{sid:<8} {verdict} {r['score']}/5  {probs}", flush=True)
            # several reviews may run at once (flow_clips reviews clips in parallel): merge only this batch's clips
            # into the file as it is now, under a file lock, and replace it in one step
            with open(rv_path + ".lock", "a") as lk:
                fcntl.flock(lk, fcntl.LOCK_EX)
                cur = json.load(open(rv_path, encoding="utf-8")) if os.path.exists(rv_path) else {}
                cur.update({it["id"]: reviews[it["id"]] for it, *_ in batch if it["id"] in reviews})
                json.dump(cur, open(rv_path + ".tmp", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
                os.replace(rv_path + ".tmp", rv_path)
            print(f"Xong {len(batch)} clip trong {time.time() - t0:.0f}s", flush=True)

    with ThreadPoolExecutor(max(1, min(4, workers))) as ex:
        list(ex.map(run_batch, batches))


def parse_script_blocks(script_text):
    raw = [p.strip() for p in re.split(r"\n\s*\n", script_text.strip()) if p.strip()]
    blocks = []
    for idx, p in enumerate(raw, 1):
        if p.startswith("#"):
            continue
        clean = re.sub(r"\[src:[^\]]*\]", "", p).strip()
        m = re.match(r"^\[(\d+)\]\s*(.*)", clean, re.S)
        if m:
            blocks.append((int(m.group(1)), m.group(2).strip()))
        else:
            blocks.append((len(blocks) + 1, clean))
    return blocks


def pick_render_mp4(vdir, preferred=None):
    if preferred:
        p = preferred if os.path.isabs(preferred) else os.path.join(WS, preferred)
        if not os.path.exists(p):
            p = os.path.join(vdir, preferred)
        if os.path.exists(p):
            return p
    rdir = os.path.join(vdir, "render")
    if not os.path.isdir(rdir):
        return None
    for name in ("final_youtube_4k.mp4", "final_tiktok_1080.mp4", "final_music_1080.mp4"):
        p = os.path.join(rdir, name)
        if os.path.exists(p):
            return p
    mp4s = [os.path.join(rdir, f) for f in os.listdir(rdir) if f.endswith(".mp4")]
    return max(mp4s, key=os.path.getmtime) if mp4s else None


def review_render(vdir, preferred_file=None):
    mp4 = pick_render_mp4(vdir, preferred_file)
    if not mp4:
        sys.exit("Chưa có file video .mp4 nào trong render/ để kiểm. Hãy bấm Dựng video 9:16 trước.")

    rdir = os.path.join(vdir, "render")
    cache_dir = os.path.join(rdir, ".review_cache")
    os.makedirs(cache_dir, exist_ok=True)

    print(f"Đang phân tích kỹ thuật & âm thanh bản dựng: {os.path.basename(mp4)}...", flush=True)
    info = probe_media(mp4)
    dur = max(1.0, info["duration"])
    audio_diag = analyze_audio(mp4, dur)
    jolt_diag = analyze_motion_jolts(mp4, fps=info["fps"] or 24.0)

    script_txt = ""
    sp = os.path.join(vdir, "script", "script.txt")
    if os.path.exists(sp):
        script_txt = open(sp, encoding="utf-8").read()
    blocks = parse_script_blocks(script_txt)
    if not blocks:
        blocks = [(i, f"(Đoạn {i})") for i in range(1, 11)]
    n_blocks = len(blocks)

    voice = next((p for p in (os.path.join(vdir, "audio", n) for n in ("voice_full.wav", "voice_full.mp3"))
                  if os.path.exists(p)), None)
    if voice:
        marks = detect_block_marks(voice, n_blocks)
        marks[-1] = min(dur, marks[-1])
    else:
        step = dur / float(n_blocks)
        marks = [i * step for i in range(n_blocks + 1)]

    all_stamps = []
    block_ranges = []
    for idx, (bnum, btxt) in enumerate(blocks):
        t0 = min(marks[idx], dur - 0.2)
        t1 = min(max(t0 + 0.4, marks[idx + 1]), dur - 0.05)
        block_ranges.append((bnum, t0, t1, btxt))
        if idx == 0:
            s_a = min(0.8, (t0 + t1) * 0.25)
            s_b = t0 + (t1 - t0) * 0.72
            all_stamps.append((s_a, f"[{bnum}A·Hook] {s_a:.1f}s"))
            all_stamps.append((s_b, f"[{bnum}B] {s_b:.1f}s"))
        else:
            s_a = t0 + (t1 - t0) * 0.28
            s_b = t0 + (t1 - t0) * 0.74
            all_stamps.append((s_a, f"[{bnum}A] {s_a:.1f}s"))
            all_stamps.append((s_b, f"[{bnum}B] {s_b:.1f}s"))

    mid = len(all_stamps) // 2
    g1 = os.path.join(cache_dir, "grid_part1.png")
    g2 = os.path.join(cache_dir, "grid_part2.png")
    print("Đang xuất 2 bảng storyboard 20 khung hình theo mốc 10 đoạn thoại...", flush=True)
    make_contact_sheet(mp4, all_stamps[:mid], g1, cols=5, tile_w=252, tile_h=448,
                       header=f"{os.path.basename(mp4)} — Nửa đầu (Đoạn 1–{blocks[mid // 2 - 1][0]})")
    make_contact_sheet(mp4, all_stamps[mid:], g2, cols=5, tile_w=252, tile_h=448,
                       header=f"{os.path.basename(mp4)} — Nửa sau (Đoạn {blocks[mid // 2][0]}–{blocks[-1][0]})")

    style_ref = load_style_ref("vn-ligne-claire")
    block_lines = [f"Đoạn [{bnum}] ({t0:.1f}s – {t1:.1f}s): {btxt}" for bnum, t0, t1, btxt in block_ranges]
    sil_str = ", ".join(f"{s['start']}s–{s['end']}s ({s['dur']}s)" for s in audio_diag["long_silences"]) or "không có khoảng lặng bất thường"
    jump_str = ", ".join(f"{j['sec']}s (f{j['frame']})" for j in jolt_diag["jumps"][:12]) or "không có"

    parts = []
    if style_ref:
        parts.append(f"Approved Channel Style Reference: {style_ref}")
    parts += [
        f"Storyboard Contact Sheet 1 (first half of video — READ THIS IMAGE): {g1}",
        f"Storyboard Contact Sheet 2 (second half of video — READ THIS IMAGE): {g2}",
        "Technical & Audio Diagnostics from FFmpeg:\n"
        f"- File: {os.path.basename(mp4)} | Duration: {dur:.2f}s | Resolution: {info['width']}x{info['height']} | FPS: {info['fps']:.1f}\n"
        f"- Audio present: {audio_diag['has_audio']} | Integrated loudness: {audio_diag['lufs']} LUFS | True peak: {audio_diag['true_peak_db']} dBTP\n"
        f"- Mid-video silences >1.25s: {sil_str}\n"
        f"- Detected hard visual cuts/jumps timestamps: {jump_str}",
        "Script Blocks & Voiceover Time Ranges:\n" + "\n".join(block_lines),
    ]

    task = (
        "You are reviewing a finished 9:16 YouTube Shorts / TikTok historical animation video. "
        "Open and inspect EVERY image file listed below using your file viewing tool. Do not edit, generate or write files.\n\n"
        f"{RENDER_RUBRIC}\n\n" + "\n\n".join(parts)
    )
    print("Đang gửi Gemini đánh giá toàn bộ bản dựng 9:16 (hình, khớp thoại 10 đoạn, nhịp cắt, âm thanh)...", flush=True)
    t0 = time.time()
    data = run_agy_json(task, RENDER_SCHEMA, cache_dir)

    b_map = {b["block"]: b for b in data.get("blocks", [])}
    merged_blocks = []
    for bnum, s0, s1, _ in block_ranges:
        br = b_map.get(bnum, {"block": bnum, "ok": True, "note": ""})
        merged_blocks.append({
            "block": bnum,
            "time": f"{s0:.1f}s–{s1:.1f}s",
            "ok": bool(br.get("ok", True)),
            "note": br.get("note", ""),
        })

    out = {
        "file": os.path.relpath(mp4, vdir),
        "mtime": os.path.getmtime(mp4),
        "at": time.strftime("%Y-%m-%d %H:%M"),
        "duration": round(dur, 2),
        "resolution": f"{info['width']}x{info['height']}",
        "fps": round(info["fps"], 1),
        "ok": bool(data.get("ok")),
        "score": int(data.get("score", 3)),
        "summary": data.get("summary", ""),
        "audio": {
            "has_audio": audio_diag["has_audio"],
            "lufs": audio_diag["lufs"],
            "true_peak_db": audio_diag["true_peak_db"],
            "long_silences": audio_diag["long_silences"],
            "verdict": data.get("audio_verdict", ""),
        },
        "pacing_verdict": data.get("pacing_verdict", ""),
        "recommend_smooth_jolts": bool(data.get("recommend_smooth_jolts")),
        "problems": data.get("problems", []),
        "fixes": data.get("fixes", []),
        "blocks": merged_blocks,
        "grids": [os.path.relpath(g1, vdir), os.path.relpath(g2, vdir)],
    }

    out_path = os.path.join(rdir, "review.json")
    json.dump(out, open(out_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    verdict = "ĐẠT" if out["ok"] else "CẦN SỬA"
    print(f"Hoàn tất kiểm bản dựng trong {time.time() - t0:.0f}s → {verdict} ({out['score']}/5): {out['summary']}", flush=True)


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    vdir = os.path.abspath(args[0])
    do_clips = "--clips" in args
    do_render = "--render" in args
    if not do_clips and not do_render:
        do_clips = os.path.isdir(os.path.join(vdir, "clips")) and any(
            f.endswith(".mp4") for f in os.listdir(os.path.join(vdir, "clips"))
        )
        do_render = os.path.isdir(os.path.join(vdir, "render")) and any(
            f.endswith(".mp4") for f in os.listdir(os.path.join(vdir, "render"))
        )
        if not do_clips and not do_render:
            sys.exit("Chưa có clip Veo (.mp4) hay bản dựng (.mp4) nào để kiểm.")

    only = set(args[args.index("--only") + 1].split(",")) if "--only" in args else None
    workers = int(args[args.index("--workers") + 1]) if "--workers" in args else 2
    pref_file = args[args.index("--file") + 1] if "--file" in args else None

    if do_clips:
        review_clips(vdir, only=only, review_all=("--all" in args), workers=workers)
    if do_render:
        review_render(vdir, preferred_file=pref_file)


if __name__ == "__main__":
    main()
