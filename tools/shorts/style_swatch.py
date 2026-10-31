#!/usr/bin/env python3
"""A neutral style swatch for a Shorts channel: the art style of its reference frames without their content.

The channel's style references (brand/banner_src/*.png) are frames of earlier videos (Cổ Loa), so the image
model sometimes copies their landscape and buildings into new scenes (Bạch Đằng S04A, 2026-10-28). The swatch
shows only line work, paint, water, earth, plants and sky in that style; once the owner approves one,
make_shorts_prompts.py attaches it instead of the old frames.

Usage:
  style_swatch.py CHANNEL_ID                 make 2 candidates in Flow (Nano Banana Pro) -> brand/style_swatch/
  style_swatch.py CHANNEL_ID --approve FILE  use FILE: copied to brand/style_swatch.png, set in channel.json
"""
import glob
import json
import os
import subprocess
import sys
import time

WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(WS, "tools"))
import flowcli  # noqa: E402

PROMPT = ("Use the attached images ONLY for their art style: line weight, ink texture, muted watercolour palette, "
          "shading and paper grain. Draw a NEW style sample sheet in exactly that style, vertical 9:16, as a loose "
          "grid of six small vignettes with soft gaps: rippling river water with foam; a bank of reeds and grass; "
          "layered earth and mud in cross-section; a rough wooden post with rope lashing; a cloudy sky over distant "
          "low hills; a clay pot and a woven basket on the ground. No buildings, walls, gates, fortresses or towers, "
          "no boats, no people or animals, no text, letters or numbers anywhere.")


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    ch = os.path.join(WS, "channels", a[0])
    out = os.path.join(ch, "brand", "style_swatch")
    if "--approve" in a:
        src = os.path.abspath(a[a.index("--approve") + 1])
        dst = os.path.join(ch, "brand", "style_swatch.png")
        subprocess.run(["sips", "-s", "format", "png", src, "--out", dst], capture_output=True, check=True)
        cj = os.path.join(ch, "channel.json")
        c = json.load(open(cj, encoding="utf-8"))
        c["style_swatch"] = os.path.relpath(dst, WS)
        json.dump(c, open(cj, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("style swatch set: %s (run make_shorts_prompts.py again for new prompts)" % c["style_swatch"])
        return 0
    refs = sorted(glob.glob(os.path.join(ch, "brand", "banner_src", "*.png")))[:3]
    if not refs:
        sys.exit("no brand/banner_src/*.png style references")
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    args = ["image", "i2i", PROMPT] + [x for r in refs for x in ("--ref", r)] + [
        "--model", "nano-pro", "--aspect", "9:16", "-n", "2", "--out", out, "--json"]
    p, res, secs = flowcli.call(args)
    got = [f for f in glob.glob(os.path.join(out, "**", "*"), recursive=True)
           if os.path.splitext(f)[1].lower() in (".png", ".jpg", ".jpeg", ".webp") and os.path.getmtime(f) >= t0 - 5]
    print("exit %s, %d candidate(s) in %d s:" % (p.returncode, len(got), secs))
    for f in got:
        print("  " + f)
    return 0 if got else 1


if __name__ == "__main__":
    sys.exit(main())
