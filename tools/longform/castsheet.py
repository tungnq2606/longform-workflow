"""The cast sheet of one project: every pose of every hero kit the project uses, pasted side by side on white.

Built from approved kit images only, never by AI (spec §4.5): it is the reference for later generations.

  python -m tools.longform.castsheet <project dir>
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

from tools.longform import images, kit

POSE_H = 480
GAP = 40
LABEL_H = 36


def _kits(pdir):
    return list(dict.fromkeys(it["kit"] for it in images.load(pdir) if it["type"] == "pose" and it.get("kit")))


def build(pdir):
    cells = []
    for kid in _kits(pdir):
        try:
            k = kit.load_kit(kid)
        except (OSError, ValueError):
            continue
        for key, im in sorted(k.get("images", {}).items()):
            f = os.path.join(kit.kit_dir(kid), im["file"])
            if os.path.isfile(f):
                cells.append(("%s / %s" % (kid, key), f))
    if not cells:
        raise ValueError("dự án chưa có tư thế nhân vật nào được duyệt")
    pics = []
    for label, f in cells:
        im = Image.open(f).convert("RGBA")
        w = max(1, round(im.size[0] * POSE_H / im.size[1]))
        pics.append((label, im.resize((w, POSE_H), Image.LANCZOS)))
    font = ImageFont.load_default()
    width = GAP + sum(max(p.size[0], 8 * len(label)) + GAP for label, p in pics)
    sheet = Image.new("RGB", (width, GAP + POSE_H + LABEL_H + GAP), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    x = GAP
    for label, p in pics:
        cell_w = max(p.size[0], 8 * len(label))
        sheet.paste(p, (x + (cell_w - p.size[0]) // 2, GAP), p)
        draw.text((x, GAP + POSE_H + 10), label, fill=(0, 0, 0), font=font)
        x += cell_w + GAP
    out = os.path.join(pdir, "images", "cast_sheet.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet.save(out)
    return out


if __name__ == "__main__":
    print(json.dumps(build(sys.argv[1])))
