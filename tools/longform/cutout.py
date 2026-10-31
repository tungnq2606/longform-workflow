"""Cut a figure out of a flat chroma-key background (hero kit images).

  python -m tools.longform.cutout SRC DST      prints {"width", "height", "anchor", "key"} as JSON

The key colour is the median of the source's border ring, so a generator that drew a slightly different green still
works. White or pale clothes stay opaque because only colours close to the key become transparent.
"""
import json
import statistics
import sys

from PIL import Image, PngImagePlugin

DEFAULT_KEY = (0, 177, 64)
RING = 4
SOLID = 128  # alpha at or above this counts as part of the figure


def _border_key(im):
    w, h = im.size
    px = im.load()
    ring = [px[x, y] for x in range(w) for y in list(range(RING)) + list(range(h - RING, h))]
    ring += [px[x, y] for y in range(RING, h - RING) for x in list(range(RING)) + list(range(w - RING, w))]
    return tuple(int(statistics.median(c[i] for c in ring)) for i in range(3))


def _dist(c, key):
    return ((c[0] - key[0]) ** 2 + (c[1] - key[1]) ** 2 + (c[2] - key[2]) ** 2) ** 0.5


def _alpha(c, key, tol):
    d = _dist(c, key)
    if d < tol:
        return 0
    if d >= tol * 1.6:
        return 255
    return int(255 * (d - tol) / (tol * 0.6))


def _mask(im, key, tol):
    """Alpha per pixel of an RGB image as a flat list (row-major)."""
    return [_alpha(c, key, tol) for c in im.getdata()]


def cut(src, dst, tol=60, pad=16):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    key = _border_key(im)
    alpha = _mask(im, key, tol)
    out = Image.new("RGBA", (w, h))
    pix = []
    for c, a in zip(im.getdata(), alpha):
        r, g, b = c
        if 0 < a < 255:  # despill: edge pixels lose the green cast
            g = min(g, max(r, b))
        pix.append((r, g, b, a))
    out.putdata(pix)
    solid = [(i % w, i // w) for i, a in enumerate(alpha) if a >= SOLID]
    if not solid:
        raise ValueError("no figure found in %s (everything matches the key %s)" % (src, key))
    x0, x1 = min(p[0] for p in solid), max(p[0] for p in solid)
    y0, y1 = min(p[1] for p in solid), max(p[1] for p in solid)
    box = (max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad + 1), min(h, y1 + pad + 1))
    out = out.crop(box)
    band = max(1, round((y1 - y0 + 1) * 0.03))
    feet = [p[0] for p in solid if p[1] > y1 - band]
    anchor = [round(sum(feet) / len(feet)) - box[0], y1 - box[1]]
    meta = PngImagePlugin.PngInfo()
    meta.add_text("chroma_key", json.dumps(list(key)))
    out.save(dst, pnginfo=meta)
    return {"width": out.size[0], "height": out.size[1], "anchor": anchor, "key": list(key)}


def check(path, source=None, tol=60):
    problems = []
    im = Image.open(path)
    key = tuple(json.loads(im.info.get("chroma_key", "null")) or DEFAULT_KEY)
    rgba = im.convert("RGBA")
    alphas = [p[3] for p in rgba.getdata()]
    if min(alphas) == 255:
        problems.append("no transparency")
    opaque = [p for p in rgba.getdata() if p[3] >= SOLID]
    if opaque:
        left = sum(1 for p in opaque if _dist(p, key) < tol)
        if left / len(opaque) > 0.005:
            problems.append("key colour left on figure (%.1f%%)" % (100.0 * left / len(opaque)))
    if source:
        s = Image.open(source).convert("RGB")
        w, h = s.size
        a = _mask(s, _border_key(s), tol)
        edge = [i for i in range(w)] + [(h - 1) * w + i for i in range(w)] + [y * w for y in range(h)] + [y * w + w - 1 for y in range(h)]
        if any(a[i] >= SOLID for i in edge):
            problems.append("touches edge")
    return problems


if __name__ == "__main__":
    print(json.dumps(cut(sys.argv[1], sys.argv[2])))
