#!/usr/bin/env python3
"""YouTube banner (2560x1440) and video watermark (150x150) for 'Công Trường Lịch Sử'.

Three video frames side by side tell the channel in one look: empty marsh (K1A), the build
(B2), the finished citadel (K4). Frames are taken from the 4K clips into banner_src/.
The name and tagline sit in a dark band inside the area every device shows (centre
1546x423, x=507-2053, y=508-931). Font: Be Vietnam Pro (SIL OFL 1.1, tools/kit/fonts).
Run: python3 brand.py  ->  banner_2560x1440.png, banner_safe_area_check.png, watermark_150.png
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(HERE, "..", "..", "..", "tools", "kit")
sys.path.insert(0, KIT)
import build_visuals as bv  # noqa: E402

FONTS = os.path.abspath(os.path.join(KIT, "fonts"))
NAME, TAG = "CÔNG TRƯỜNG LỊCH SỬ", "Hôm nay, bạn sẽ xây…"
PANELS = ["K1A", "B2", "K4"]  # before, during, after
YELLOW, INK = "#FFD23F", "#2a1a08"


def banner(check=False):
    panels = "".join(
        f'<div class="p" style="left:{i * 2560 / 3:.1f}px;background-image:url(\'file://{HERE}/banner_src/{n}.png\')"></div>'
        for i, n in enumerate(PANELS))
    seams = "".join(f'<div class="seam" style="left:{i * 2560 / 3 - 4:.1f}px"></div>' for i in (1, 2))
    box = ('<div style="position:absolute;left:507px;top:508px;width:1546px;height:423px;'
           'outline:4px dashed #e11"></div>') if check else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:'BVP';font-weight:900;src:url('file://{FONTS}/BeVietnamPro-Black.ttf')}}
@font-face{{font-family:'BVP';font-weight:800;src:url('file://{FONTS}/BeVietnamPro-ExtraBold.ttf')}}
html,body{{margin:0;width:2560px;height:1440px;overflow:hidden;background:#000}}
.p{{position:absolute;top:0;width:{2560 / 3:.1f}px;height:1440px;background-size:cover;background-position:center 40%}}
.seam{{position:absolute;top:0;width:8px;height:1440px;background:{INK}}}
.band{{position:absolute;left:0;right:0;top:575px;height:290px;
  background:linear-gradient(to bottom,rgba(20,14,6,0),rgba(20,14,6,.78) 18%,rgba(20,14,6,.78) 82%,rgba(20,14,6,0))}}
.t{{position:absolute;left:0;right:0;text-align:center;font-family:'BVP';line-height:1;white-space:nowrap}}
.name{{top:618px;font-weight:900;font-size:116px;color:{YELLOW};
  -webkit-text-stroke:8px {INK};paint-order:stroke fill;text-shadow:0 8px 20px rgba(0,0,0,.5)}}
.tag{{top:772px;font-weight:800;font-size:54px;color:#fff;letter-spacing:1px}}
</style></head><body>{panels}{seams}<div class="band"></div>
<div class="t name">{NAME}</div><div class="t tag">{TAG}</div>{box}</body></html>"""


def watermark():
    # YouTube video watermark (150x150, transparent): the brand's yellow hard hat on a dark
    # disc, no text (text is unreadable at the size YouTube shows it).
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;background:transparent}}svg{{display:block}}</style></head><body>
<svg width="150" height="150" viewBox="0 0 150 150" xmlns="http://www.w3.org/2000/svg">
<circle cx="75" cy="75" r="70" fill="{INK}" stroke="{YELLOW}" stroke-width="6"/>
<path d="M33 92 Q33 46 75 44 Q117 46 117 92 Z" fill="{YELLOW}" stroke="{INK}" stroke-width="4"/>
<path d="M66 45 L66 90 M84 45 L84 90" stroke="#e0b11f" stroke-width="7"/>
<rect x="22" y="88" width="106" height="14" rx="7" fill="{YELLOW}" stroke="{INK}" stroke-width="4"/>
</svg></body></html>"""


if __name__ == "__main__":
    for name, html, w, h in [("banner_2560x1440", banner(), 2560, 1440),
                             ("banner_safe_area_check", banner(True), 2560, 1440),
                             ("watermark_150", watermark(), 150, 150)]:
        hp = os.path.join(HERE, name + ".html")
        open(hp, "w", encoding="utf-8").write(html)
        bv.render(hp, os.path.join(HERE, name + ".png"), w, h, transparent=name.startswith("watermark"))
    print("ok")
