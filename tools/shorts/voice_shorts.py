#!/usr/bin/env python3
"""Shorts voice helper for Công Trường Lịch Sử (Vbee 2-part under-1-min workflow).

Usage:
  voice_shorts.py VIDEO_DIR          script/script.txt -> script/voiceover_tts/{01..NN,part1,part2,full}.txt
  voice_shorts.py VIDEO_DIR --join   join audio/vbee_parts/part1.* + part2.* -> audio/voice_full.wav
"""
import array
import glob
import os
import re
import subprocess
import sys
import tempfile
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(os.path.dirname(HERE))
FFMPEG_DIR = os.path.join(WS, "tools", "anim", "node_modules", "@remotion", "compositor-darwin-arm64")
FFMPEG = os.path.join(FFMPEG_DIR, "ffmpeg") if os.path.exists(os.path.join(FFMPEG_DIR, "ffmpeg")) else "ffmpeg"

RATE = 44100
GAP = 0.93
QUIET = 10 ** (-35 / 20) * 32768
PEAK = -1.5


def voice_cfg(vdir):
    """The channel's Vbee settings (channel.json "voice"): speed to set in Vbee and the speaking rate it gives."""
    d = os.path.abspath(vdir)
    while d != os.path.dirname(d):
        cj = os.path.join(d, "channel.json")
        if os.path.exists(cj):
            import json
            v = json.load(open(cj, encoding="utf-8")).get("voice", {})
            speed = float(v.get("speed", 1.0))
            return speed, float(v.get("syllables_per_sec_at_1x", 3.9 / 1.13)) * speed
        d = os.path.dirname(d)
    return 1.13, 3.9


def parse_blocks(script_path):
    raw = open(script_path, encoding="utf-8").read()
    lines = [l.strip() for l in raw.splitlines() if not l.strip().startswith("#")]
    cleaned = "\n".join(lines).strip()
    paras = [p.strip() for p in re.split(r"\n\s*\n", cleaned) if p.strip()]
    blocks = []
    for p in paras:
        p = re.sub(r"^\[\d+\]\s*", "", p)
        p = re.sub(r"\[src:[^\]]*\]", "", p)
        p = re.sub(r"\s+", " ", p).strip()
        if p:
            blocks.append(p)
    return blocks


def build_tts(vdir):
    sp = os.path.join(vdir, "script", "script.txt")
    if not os.path.exists(sp):
        sys.exit(f"missing {sp}")
    blocks = parse_blocks(sp)
    if not blocks:
        sys.exit("script.txt has 0 blocks")
    out = os.path.join(vdir, "script", "voiceover_tts")
    os.makedirs(out, exist_ok=True)
    for i, b in enumerate(blocks, 1):
        open(os.path.join(out, f"{i:02d}.txt"), "w", encoding="utf-8").write(b + "\n")
    mid = len(blocks) // 2
    p1, p2 = blocks[:mid], blocks[mid:]
    open(os.path.join(out, "part1.txt"), "w", encoding="utf-8").write("\n\n".join(p1) + "\n")
    open(os.path.join(out, "part2.txt"), "w", encoding="utf-8").write("\n\n".join(p2) + "\n")
    open(os.path.join(out, "full.txt"), "w", encoding="utf-8").write("\n\n".join(blocks) + "\n")
    w1 = sum(len(x.split()) for x in p1)
    w2 = sum(len(x.split()) for x in p2)
    speed, rate = voice_cfg(vdir)
    print(f"Vbee: đặt tốc độ {speed} cho cả 2 phần (chuẩn của kênh, {rate:.2f} âm tiết/giây)")
    print(f"{len(blocks)} đoạn | Tổng {w1 + w2} âm tiết (~{round((w1 + w2) / rate)}s)")
    for name, w, rng in (("part1", w1, f"1-{mid}"), ("part2", w2, f"{mid + 1}-{len(blocks)}")):
        sec = w / rate
        print(f"  {name}.txt (đoạn {rng}): {w} âm tiết (~{round(sec)}s - {'an toàn' if sec < 57 else 'QUÁ DÀI'} < 60s Vbee)")


def decode_mono(path):
    env = dict(os.environ, DYLD_LIBRARY_PATH=FFMPEG_DIR)
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "part.wav")
        subprocess.run([FFMPEG, "-v", "error", "-i", path, "-ac", "1", "-ar", str(RATE), "-c:a", "pcm_s16le", wav],
                       check=True, env=env)
        with wave.open(wav) as w:
            return array.array("h", w.readframes(w.getnframes()))


def trim_silence(s, start, end):
    keep = int(0.03 * RATE)
    a, b = 0, len(s)
    if start:
        while a < b and abs(s[a]) < QUIET:
            a += 1
        a = max(0, a - keep)
    if end:
        while b > a and abs(s[b - 1]) < QUIET:
            b -= 1
        b = min(len(s), b + keep)
    return s[a:b]


def join_parts(vdir):
    pdir = os.path.join(vdir, "audio", "vbee_parts")
    parts = []
    for tag in ("part1", "part2"):
        matches = sorted(glob.glob(os.path.join(pdir, tag + ".*")))
        if not matches:
            sys.exit(f"Chưa có file {tag} trong audio/vbee_parts/ (cần part1 và part2)")
        parts.append(matches[-1])
    out = array.array("h")
    for k, path in enumerate(parts):
        s = trim_silence(decode_mono(path), start=k > 0, end=k < len(parts) - 1)
        if k:
            out.extend([0] * int(GAP * RATE))
        print(f"{os.path.basename(path)}: {len(s) / RATE:.2f} s")
        out.extend(s)
    peak_val = max(abs(x) for x in out) or 1
    gain = 10 ** (PEAK / 20) * 32767 / peak_val
    out = array.array("h", (max(-32767, min(32767, int(x * gain))) for x in out))
    stereo = array.array("h", bytes(len(out) * 4))
    stereo[0::2] = out
    stereo[1::2] = out
    dst = os.path.join(vdir, "audio", "voice_full.wav")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with wave.open(dst, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(stereo.tobytes())
    print(f"Đã ghép -> audio/voice_full.wav ({len(out) / RATE:.2f} s, gain {gain:.2f}x)")
    sp = os.path.join(vdir, "script", "script.txt")
    if os.path.exists(sp):  # a different Vbee speed shows up as a length off the channel's standard
        speed, rate = voice_cfg(vdir)
        syl = sum(len(x.split()) for x in parse_blocks(sp))
        got = syl / max(1.0, len(out) / RATE)
        if abs(got / rate - 1) > 0.1:
            print(f"CẢNH BÁO: giọng đọc {got:.2f} âm tiết/giây, chuẩn kênh {rate:.2f} (tốc độ Vbee {speed}). "
                  f"Kiểm tra lại tốc độ trong Vbee.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: voice_shorts.py VIDEO_DIR [--join]")
    vdir = os.path.abspath(sys.argv[1])
    if "--join" in sys.argv[2:]:
        join_parts(vdir)
    else:
        build_tts(vdir)
