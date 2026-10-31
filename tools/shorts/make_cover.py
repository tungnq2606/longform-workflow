#!/usr/bin/env python3
"""Render a 1080x1920 Shorts/TikTok cover image in Be Vietnam Pro (#FFD23F + white).

Usage:
  make_cover.py VIDEO_DIR --line1 "ĐÓNG CỌC BẠCH ĐẰNG" --line2 "THẾ NÀO?" [--bg REL_OR_ABS_IMAGE]
"""
import argparse
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(os.path.dirname(HERE))
KIT = os.path.join(WS, "tools", "kit")
sys.path.insert(0, KIT)
import build_visuals as bv  # noqa: E402

FONTS = os.path.join(KIT, "fonts")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vdir")
    ap.add_argument("--line1", default="")
    ap.add_argument("--line2", default="")
    ap.add_argument("--bg", default="")
    ns = ap.parse_args()

    vdir = os.path.abspath(ns.vdir)
    pdir = os.path.join(vdir, "packaging")
    os.makedirs(pdir, exist_ok=True)
    bg_dst = os.path.join(pdir, "cover_frame.png")

    if ns.bg:
        src = ns.bg if os.path.isabs(ns.bg) else os.path.join(WS, ns.bg)
        if not os.path.exists(src):
            src = os.path.join(vdir, ns.bg)
        if not os.path.exists(src):
            sys.exit(f"Không tìm thấy ảnh nền: {ns.bg}")
        if os.path.abspath(src) != os.path.abspath(bg_dst):
            shutil.copy2(src, bg_dst)

    if not os.path.exists(bg_dst):
        # Pick the first available generated frame automatically
        fdir = os.path.join(vdir, "images", "frames")
        frames = sorted(f for f in os.listdir(fdir) if f.endswith(".png")) if os.path.isdir(fdir) else []
        if not frames:
            sys.exit("Chưa có packaging/cover_frame.png hoặc ảnh cảnh nào để làm ảnh bìa.")
        shutil.copy2(os.path.join(fdir, frames[-1]), bg_dst)

    # Read defaults from existing cover.py if line1/line2 omitted
    cpy = os.path.join(pdir, "cover.py")
    l1, l2 = ns.line1.strip(), ns.line2.strip()
    if (not l1 or not l2) and os.path.exists(cpy):
        txt = open(cpy, encoding="utf-8").read()
        m = re.search(r'LINE1,\s*LINE2\s*=\s*"([^"]*)",\s*"([^"]*)"', txt)
        if m:
            l1 = l1 or m.group(1)
            l2 = l2 or m.group(2)
    l1 = l1 or "CÔNG TRƯỜNG"
    l2 = l2 or "LỊCH SỬ"

    s1 = 88 if len(l1) <= 14 else (76 if len(l1) <= 19 else 64)
    s2 = 128 if len(l2) <= 11 else (108 if len(l2) <= 14 else 90)

    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:'BVP';font-weight:900;src:url('file://{FONTS}/BeVietnamPro-Black.ttf')}}
@font-face{{font-family:'BVP';font-weight:800;src:url('file://{FONTS}/BeVietnamPro-ExtraBold.ttf')}}
html,body{{margin:0;width:1080px;height:1920px;overflow:hidden;background:#000}}
.bg{{position:absolute;inset:0;background:url('file://{bg_dst}') center/cover}}
.shade{{position:absolute;left:0;right:0;top:1020px;bottom:0;
  background:linear-gradient(to bottom,rgba(20,14,6,0) 0%,rgba(20,14,6,.74) 22%,rgba(20,14,6,.74) 60%,rgba(20,14,6,.38) 100%)}}
.t{{position:absolute;left:24px;right:24px;text-align:center;font-family:'BVP';line-height:1.05;white-space:nowrap}}
.l1{{top:1165px;font-weight:800;font-size:{s1}px;color:#fff;letter-spacing:1.5px;
  text-shadow:0 6px 18px rgba(0,0,0,.6)}}
.l2{{top:1268px;font-weight:900;font-size:{s2}px;color:#FFD23F;
  -webkit-text-stroke:10px #2a1a08;paint-order:stroke fill;text-shadow:0 10px 24px rgba(0,0,0,.55)}}
</style></head><body><div class="bg"></div><div class="shade"></div>
<div class="t l1">{l1}</div><div class="t l2">{l2}</div></body></html>"""

    hp = os.path.join(pdir, "cover.html")
    out_png = os.path.join(pdir, "cover_1080x1920.png")
    open(hp, "w", encoding="utf-8").write(html)
    bv.render(hp, out_png, 1080, 1920)
    print(f"Đã tạo ảnh bìa 1080x1920: {out_png}")


if __name__ == "__main__":
    main()
