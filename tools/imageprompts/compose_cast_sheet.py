#!/usr/bin/env python3
"""Paste a video's approved model sheets together into its cast sheet, so no character is ever redrawn.

Usage: compose_cast_sheet.py VIDEO_DIR      (normally not needed: agy_images.py runs compose() itself)

agy_images.py calls compose() as soon as the last model sheet is approved (or on --compose) and files the
result as the approved cast sheet. compose() lays the sheets from images/refs/ out in a grid on one 2752x1536
white image with headless Edge and also writes a "figures" version for scene references, where each person's
sheet is cut above its expression-head row (Gemini copied labelled heads into scenes).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit"))
from build_visuals import render  # noqa: E402

W, H = 2752, 1536  # Nano Banana Pro 2K 16:9, the size of the model sheets
FIGURES = 0.79  # share of a person's model sheet above the expression-head row (same cut as croptop)


def compose(video_dir):
    """Return (cast_sheet_png, figures_png) in images/runs/compose/, or raise ValueError with the reason."""
    img = os.path.join(os.path.abspath(video_dir), "images")
    items = json.load(open(os.path.join(img, "prompts", "manifest.json"), encoding="utf-8"))["items"]
    sheet = next((i for i in items if i["kind"] == "cast_sheet"), None)
    if not sheet or sheet.get("route") != "compose":
        raise ValueError("manifest has no composed cast sheet: run make_prompts.py first")
    missing = [r for r in sheet["refs"] if not os.path.exists(os.path.join(img, r))]
    if missing:
        raise ValueError("approve these model sheets first: " + ", ".join(missing))
    kinds = {c["name"]: c.get("kind") for c in json.load(open(os.path.join(img, "cast.json"), encoding="utf-8"))["characters"]}
    n = len(sheet["refs"])
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    work = os.path.join(img, "runs", "compose")
    os.makedirs(work, exist_ok=True)
    out = []
    for tag, cut in (("cast_sheet", False), ("cast_sheet_figures", True)):
        cells = ""
        for r, name in zip(sheet["refs"], sheet["characters"]):
            f = FIGURES if cut and kinds.get(name) != "animal" else 1.0
            # a box with the (cut) sheet's aspect ratio; the image overflows it at the bottom and is hidden
            cells += ('<div class="c"><div class="b" style="aspect-ratio:%d/%d"><img src="file://%s"></div></div>'
                      % (W, round(H * f), os.path.join(img, r)))
        page = ("<!doctype html><html><head><style>html,body{margin:0;background:#fff}"
                ".g{display:grid;grid-template-columns:repeat(%d,1fr);grid-template-rows:repeat(%d,1fr);width:%dpx;height:%dpx}"
                ".c{display:flex;align-items:center;justify-content:center;overflow:hidden;min-width:0;min-height:0}"
                ".b{max-width:100%%;max-height:100%%;width:100%%;overflow:hidden}.b img{width:100%%;display:block}"
                "</style></head><body><div class=\"g\">%s</div></body></html>" % (cols, rows, W, H, cells))
        hp, png = os.path.join(work, tag + ".html"), os.path.join(work, tag + ".png")
        open(hp, "w", encoding="utf-8").write(page)
        if os.path.exists(png):
            os.remove(png)
        if not render(hp, png, W, H):
            raise ValueError("headless Edge did not write " + png)
        out.append(png)
    return tuple(out)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    try:
        print("\n".join(compose(sys.argv[1])))
    except ValueError as e:
        sys.exit(str(e))
