#!/usr/bin/env python3
"""Render a 9:16 Shorts video from Veo clips (and/or still 9:16 images) timed to voice_full.

Works at every production stage:
- Early animatic: uses generated 9:16 PNG frames (converted to 24fps temp clips with slow holdZoom)
- Hybrid draft: mixes finished Veo .mp4 clips in clips/ with remaining 9:16 PNG frames
- Final export: assembles all Veo .mp4 clips + voice_full.wav -> final_tiktok_1080.mp4 & final_music_1080.mp4

Usage:
  render_shorts.py VIDEO_DIR [--music FILENAME]   -> render/final_tiktok_1080.mp4 + render/final_youtube_4k.mp4
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(os.path.dirname(HERE))
ASSEMBLE = os.path.join(WS, "tools", "editor", "assemble.swift")
FFMPEG_DIR = os.path.join(WS, "tools", "anim", "node_modules", "@remotion", "compositor-darwin-arm64")
FFMPEG = os.path.join(FFMPEG_DIR, "ffmpeg") if os.path.exists(os.path.join(FFMPEG_DIR, "ffmpeg")) else "ffmpeg"
FPS = 24
TAIL = 1.0


def ff_env():
    return dict(os.environ, DYLD_LIBRARY_PATH=FFMPEG_DIR)


def media_duration(path):
    out = subprocess.run([FFMPEG, "-hide_banner", "-i", path], capture_output=True, text=True, env=ff_env()).stderr
    m = re.search(r"Duration: (\d+):(\d+):([0-9.]+)", out)
    if not m:
        return 0.0
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def detect_block_marks(voice_path, n_blocks):
    out = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", voice_path, "-af", "silencedetect=noise=-35dB:d=0.45", "-f", "null", "-"],
        capture_output=True, text=True, env=ff_env()
    ).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", out)]
    total = media_duration(voice_path)
    pauses = [(e - s, (s + e) / 2) for s, e in zip(starts, ends) if 0.3 < e < total - 0.3]
    need = n_blocks - 1
    if len(pauses) >= need:
        mids = sorted(m for _, m in sorted(pauses, reverse=True)[:need])
        last_word = starts[-1] if len(starts) > len(ends) or (ends and ends[-1] >= total - 0.05) else total
        print("Mốc ngắt đoạn (s):", " ".join(f"{m:.2f}" for m in mids), f"| hết giọng {last_word:.2f}s")
        return [0.0] + mids + [last_word + TAIL]
    print(f"Cảnh báo: tìm thấy {len(pauses)}/{need} khoảng nghỉ dài, chia đều theo độ dài dự kiến.")
    step = (total + TAIL) / n_blocks
    return [i * step for i in range(n_blocks + 1)]


def still_to_mp4(png_path, cache_dir, sid, seconds=8.0):
    os.makedirs(cache_dir, exist_ok=True)
    dst = os.path.join(cache_dir, f"{sid}_still.mp4")
    if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(png_path):
        return dst
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p"
    subprocess.run(
        [FFMPEG, "-y", "-v", "error", "-loop", "1", "-framerate", str(FPS), "-i", png_path,
         "-t", f"{seconds:.2f}", "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", dst],
        check=True, env=ff_env()
    )
    return dst


def normalize_clip_size(src_mp4, cache_dir, sid, w=1080, h=1920):
    """Ensure every clip in one assemble.swift run shares identical pixel dimensions (1080x1920)."""
    out = subprocess.run(["sips", "-g", "pixelWidth", src_mp4], capture_output=True, text=True).stdout
    info = subprocess.run([FFMPEG, "-hide_banner", "-i", src_mp4], capture_output=True, text=True, env=ff_env()).stderr
    m = re.search(r" (\d{3,4})x(\d{3,4})", info)
    if m and (int(m.group(1)), int(m.group(2))) == (w, h):
        return src_mp4
    os.makedirs(cache_dir, exist_ok=True)
    dst = os.path.join(cache_dir, f"{sid}_{w}x{h}.mp4")
    if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src_mp4):
        return dst
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},format=yuv420p"  # bundled ffmpeg has no fps filter
    subprocess.run(
        [FFMPEG, "-y", "-v", "error", "-i", src_mp4, "-vf", vf, "-r", str(FPS), "-an", "-c:v", "libx264", "-crf", "16", dst],
        check=True, env=ff_env()
    )
    return dst


def channel_clip_sound(vdir):
    """channel.json "clip_sound": level of the Veo clips' own sound under the voice (0 = muted, the old way)."""
    d = os.path.abspath(vdir)
    while d != os.path.dirname(d):
        cj = os.path.join(d, "channel.json")
        if os.path.exists(cj):
            return float(json.load(open(cj, encoding="utf-8")).get("clip_sound", 0) or 0)
        d = os.path.dirname(d)
    return 0.0


def build_sfx_bed(clips_spec, audio_src, out_wav):
    """One track with every Veo clip's own sound at its place in the timeline: each part trimmed like its picture,
    normalised to -23 LUFS (Veo clips differ by up to 12 dB), faded at both ends, overlapping at dissolves."""
    starts, prev_end = [], 0
    for i, part in enumerate(clips_spec):
        st = 0 if i == 0 else prev_end - int(part.get("xfade", 0))
        starts.append(st)
        prev_end = st + (part["out"] - part["in"]) + int(part.get("freeze", 0))
    total = prev_end / FPS
    inputs, chains, n = [], [], 0
    for part, st, src in zip(clips_spec, starts, audio_src):
        if not src:
            continue
        info = subprocess.run([FFMPEG, "-hide_banner", "-i", src], capture_output=True, text=True, env=ff_env()).stderr
        if "Audio:" not in info:
            continue
        a, b = part["in"] / FPS, part["out"] / FPS
        d = b - a
        fade_in = max(0.15, int(part.get("xfade", 0)) / FPS)
        inputs += ["-i", src]
        ms = int(st / FPS * 1000)
        chains.append(f"[{n}:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
                      f"loudnorm=I=-23:TP=-3,aresample=48000,"
                      f"volume='min(1,min(t/{fade_in:.2f},({d:.3f}-t)/0.25))':eval=frame,adelay={ms}|{ms}[p{n}]")
        n += 1
    if not n:
        return None
    graph = ";".join(chains) + ";" + "".join(f"[p{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0,atrim=0:{total:.3f}[out]"
    subprocess.run([FFMPEG, "-y", "-v", "error"] + inputs + ["-filter_complex", graph, "-map", "[out]", "-ar", "48000", out_wav],
                   check=True, env=ff_env())
    return out_wav


def find_music(vdir, preferred=None):
    dirs = [
        os.path.join(vdir, "audio", "music"),
        os.path.join(os.path.dirname(vdir), "audio", "music"),
        os.path.join(os.path.dirname(vdir), "test-001-co-loa", "audio", "music"),
    ]
    if preferred:
        for d in dirs:
            p = os.path.join(d, preferred)
            if os.path.exists(p):
                return p
    for d in dirs:
        if os.path.isdir(d):
            for n in ("zhuge_fuqin.mp3", "Investigations.mp3"):
                if os.path.exists(os.path.join(d, n)):
                    return os.path.join(d, n)
            mp3s = sorted(f for f in os.listdir(d) if f.endswith(".mp3"))
            if mp3s:
                return os.path.join(d, mp3s[0])
    return None


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit("usage: render_shorts.py VIDEO_DIR [--music FILE] [--smooth]")
    vdir = os.path.abspath(args[0])
    smooth = "--smooth" in args
    music_name = None
    if "--music" in args:
        idx = args.index("--music")
        if idx + 1 < len(args):
            music_name = args[idx + 1]

    # If this video already has its own custom render/timeline.py (like test-001-co-loa), run it directly
    custom_tl = os.path.join(vdir, "render", "timeline.py")
    if os.path.exists(custom_tl) and not os.path.exists(os.path.join(vdir, "images", "shots.json")):
        rdir = os.path.join(vdir, "render")
        subprocess.run([sys.executable, custom_tl], cwd=rdir, check=True)
        jolts_py = os.path.join(WS, "tools", "editor", "split_jolts.py")
        for spec_name in ("final_tiktok.json", "final_music.json"):
            sp = os.path.join(rdir, spec_name)
            if os.path.exists(sp):
                if smooth and os.path.exists(jolts_py):
                    subprocess.run([sys.executable, jolts_py, sp, sp], cwd=rdir, check=True)
                subprocess.run(["swift", ASSEMBLE, sp], cwd=rdir, check=True)
        return

    man_path = os.path.join(vdir, "images", "prompts", "manifest.json")
    if not os.path.exists(man_path):
        sys.exit("Chưa có manifest.json. Hãy bấm 'Tạo lại prompt' trước.")
    man = json.load(open(man_path, encoding="utf-8"))
    items = man.get("items", [])
    by_id = {it["id"]: it for it in items}

    cr_path = os.path.join(vdir, "images", "runs", "clip_review.json")
    clip_reviews = json.load(open(cr_path, encoding="utf-8")) if os.path.exists(cr_path) else {}

    voice = next((p for p in (os.path.join(vdir, "audio", n) for n in ("voice_full.wav", "voice_full.mp3"))
                  if os.path.exists(p)), None)

    n_blocks = max((it.get("block", 1) for it in items), default=10)
    if voice:
        marks = detect_block_marks(voice, n_blocks)
    else:
        print("Chưa có audio/voice_full.wav — dựng bản nháp hình theo thời lượng dự kiến.")
        marks = [0.0]
        for b in range(1, n_blocks + 1):
            bdur = sum(float(it.get("duration", 4.5)) for it in items if it.get("block") == b) or 8.0
            if b == 1 and man.get("hook_reuse"):
                bdur += float(man["hook_reuse"].get("duration", 2.2))
            marks.append(marks[-1] + bdur)

    # Build ordered sequence of shots (including optional Block 1 hook reuse, e.g. S08B 2.2s -> S01)
    seq = []
    hook = man.get("hook_reuse")
    for b in range(1, n_blocks + 1):
        b_shots = []
        if b == 1 and hook and hook.get("shot_id") in by_id:
            src_it = dict(by_id[hook["shot_id"]])
            src_it["duration"] = float(hook.get("duration", 2.2))
            src_it["xfade"] = 0
            src_it["_label"] = f"hook ({src_it['id']})"
            b_shots.append(src_it)
        for it in items:
            if it.get("block", 1) == b:
                c = dict(it)
                if b == 1 and b_shots:
                    c["xfade"] = 0  # hard cut from hook into S01
                b_shots.append(c)
        if not b_shots:
            continue
        w_sum = sum(float(x.get("duration", 4.5)) for x in b_shots) or 1.0
        b_start, b_end = marks[b - 1], marks[b]
        acc = 0.0
        for x in b_shots:
            acc += float(x.get("duration", 4.5))
            end_sec = b_start + (b_end - b_start) * (acc / w_sum)
            seq.append((x, round(end_sec * FPS)))

    rdir = os.path.join(vdir, "render")
    cache_dir = os.path.join(rdir, ".cache_1080")
    os.makedirs(rdir, exist_ok=True)

    clips_spec = []
    audio_src = []  # source clip of each part (None for stills): the clips' own sound bed
    prev_end = 0
    n_veo, n_still, n_seams, missing = 0, 0, 0, []
    seams, blend = (64, 128), 4

    for idx, (it, end_at) in enumerate(seq):
        sid = it["id"]
        clip_p = os.path.join(vdir, "clips", f"{sid}.mp4")
        img_p = os.path.join(vdir, "images", it["save_as"])
        is_veo = False
        if os.path.exists(clip_p):
            media = normalize_clip_size(clip_p, cache_dir, sid)
            avail = max(24, int(media_duration(media) * FPS) - 4)  # trim last 4 frames to avoid tail jolt
            cr = clip_reviews.get(sid)
            if cr and abs(cr.get("mtime", 0) - os.path.getmtime(clip_p)) < 1 and float(cr.get("trim_out_sec") or 0) >= 1.8:
                t_frames = int(float(cr["trim_out_sec"]) * FPS)
                if 24 <= t_frames < avail:
                    print(f"Cắt đuôi clip {sid} tại {cr['trim_out_sec']:.1f}s theo góp ý Gemini.")
                    avail = t_frames
            n_veo += 1
            is_veo = True
        elif os.path.exists(img_p):
            media = still_to_mp4(img_p, cache_dir, sid, seconds=10.0)
            avail = 10 * FPS
            n_still += 1
        else:
            missing.append(sid)
            continue

        xfade = int(it.get("xfade", 12)) if clips_spec else 0
        start = prev_end - xfade if clips_spec else 0
        need = max(12, end_at - start)

        # Optional Veo chunk-seam smoothing (frames 64 & 128) while preserving exact timeline end_at
        cuts = []
        if smooth and is_veo:
            tentative = min(need + len(seams) * blend, avail)
            cuts = [s for s in seams if blend < s < tentative - (blend + 14)]
            need_src = need + len(cuts) * blend
            play = min(need_src, avail)
            cuts = [s for s in cuts if blend < s < play - (blend + 14)]
            need_src = need + len(cuts) * blend
            play = min(need_src, avail)
            freeze = max(0, need_src - play)
        else:
            play = min(need, avail)
            freeze = max(0, need - play)

        if clips_spec and 0 < freeze <= max(0, xfade - 6):
            xfade, start, need, freeze = xfade - freeze, start + freeze, play - len(cuts) * blend, 0

        edges = [0] + cuts + [play]
        for k in range(len(edges) - 1):
            part = {
                "file": media,
                "in": edges[k],
                "out": edges[k + 1],
                "xfade": xfade if k == 0 else blend,
                "note": (it.get("_label") or sid) if k == 0 else f"{sid} seam {edges[k]}",
            }
            if k == 0 and freeze > 0:
                part["freeze"] = freeze
            clips_spec.append(part)
            audio_src.append(clip_p if is_veo else None)
        n_seams += len(cuts)
        prev_end = start + freeze + play - len(cuts) * blend

    if not clips_spec:
        sys.exit(f"Chưa có ảnh hay clip Veo nào để dựng (thiếu: {', '.join(missing[:8])}...). Hãy tạo ảnh hoặc tải clip lên trước.")
    if missing:
        print(f"Lưu ý: bỏ qua {len(missing)} cảnh chưa có ảnh/clip: {', '.join(missing)}")

    seam_note = f", khử {n_seams} điểm giật seam Veo" if n_seams else ""
    print(f"Đang ghép {n_veo} clip Veo + {n_still} ảnh tĩnh zoom nhẹ{seam_note}, dài {prev_end / FPS:.1f}s...")
    base_spec = {
        "fps": FPS,
        "width": 1080,
        "height": 1920,
        "mbps": 16,
        "holdZoom": 1.05,
        "muteClips": True,
        "clips": clips_spec,
    }

    audio_tracks = [{"file": voice, "at": 0, "volume": 1.0}] if voice else []
    level = channel_clip_sound(vdir)
    if level > 0:  # owner, 2026-10-29: keep the clips' water/wind/hammer sound quietly under the voice
        bed = build_sfx_bed(clips_spec, audio_src, os.path.join(cache_dir, "clip_sound_bed.wav"))
        if bed:
            audio_tracks.append({"file": bed, "at": 0, "volume": level})
            print(f"Giữ tiếng clip Veo ở mức {level} so với giọng (đã chuẩn hoá độ to từng clip).")
    # Two files with the same full sound (voice + music + clips' own sound), owner 2026-10-29:
    # TikTok 1080x1920, YouTube 4K 2160x3840 (uploads of 1440p and up get YouTube's higher-bitrate encode).
    music_file = find_music(vdir, music_name)
    if music_file and voice:
        audio_tracks = audio_tracks + [{"file": music_file, "at": 0, "volume": 0.068, "fadeOut": 2.5}]
    note = f" (nhạc {os.path.basename(music_file)})" if music_file and voice else ""
    for out_name, extra in (("final_tiktok_1080", {}), ("final_youtube_4k", {"width": 2160, "height": 3840, "mbps": 45})):
        spec = dict(base_spec, out=os.path.join(rdir, out_name + ".mp4"), audio=audio_tracks, **extra)
        spec_json = os.path.join(rdir, out_name.rsplit("_", 1)[0] + ".json")
        json.dump(spec, open(spec_json, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        subprocess.run(["swift", ASSEMBLE, spec_json], cwd=rdir, check=True)
        print(f"Đã xuất{note}:", spec["out"])
    for old in ("final_music_1080.mp4", "final_music.json"):  # replaced by the 4K YouTube copy
        if os.path.exists(os.path.join(rdir, old)):
            os.remove(os.path.join(rdir, old))


if __name__ == "__main__":
    main()
