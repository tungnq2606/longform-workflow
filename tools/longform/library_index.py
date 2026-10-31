"""What the shared library holds, for Studio's home page: hero kits, reusable backgrounds, style locks, thumbnails.

Thumbnails are made with Pillow and cached in <state>/thumbs/. Callers pass a kind and an id; the file is looked up
from the library listing, never built from the caller's text, so no path can escape the library.
"""
import glob
import json
import os

from PIL import Image

from tools.longform import paths

THUMB_W = {"bg": 1600}
THUMB_H = {"char": 480}


def _json(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _characters():
    out = {}
    for p in sorted(glob.glob(os.path.join(paths.library(), "characters", "*", "kit.json"))):
        k = _json(p)
        if k and k.get("images"):
            out[os.path.basename(os.path.dirname(p))] = (k, os.path.dirname(p))
    return out


def _backgrounds():
    return {os.path.splitext(os.path.basename(p))[0]: p
            for p in sorted(glob.glob(os.path.join(paths.library(), "backgrounds", "*.png")))}


def summary():
    chars = [{"id": cid, "name": k.get("name", cid), "poses": len(k["images"])} for cid, (k, _) in _characters().items()]
    styles = []
    for p in sorted(glob.glob(os.path.join(paths.library(), "style", "*.json"))):
        s = _json(p)
        if s:
            styles.append({"id": s.get("id", os.path.basename(p)[:-5]), "approved": bool(s.get("approved"))})
    return {"characters": chars, "backgrounds": [{"id": b} for b in _backgrounds()], "styles": styles}


def _source(kind, item):
    if kind == "bg":
        return _backgrounds()[item]
    if kind == "char":
        k, d = _characters()[item]
        first = next(iter(k["images"].values()))
        return os.path.join(d, first["file"])
    raise KeyError(kind)


def thumb(kind, item):
    """Path of a cached thumbnail; KeyError when the kind or id is not in the library."""
    src = _source(kind, item)
    ext = ".jpg" if kind == "bg" else ".png"
    out_dir = os.path.join(paths.state(), "thumbs")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "%s-%s%s" % (kind, item, ext))
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
        return out
    with Image.open(src) as im:
        w, h = im.size
        size = (THUMB_W[kind], round(h * THUMB_W[kind] / w)) if kind == "bg" else (round(w * THUMB_H[kind] / h), THUMB_H[kind])
        small = im.resize(size, Image.LANCZOS)
        if kind == "bg":
            small.convert("RGB").save(out + ".tmp", "JPEG", quality=85)
        else:
            small.convert("RGBA").save(out + ".tmp", "PNG")
    os.replace(out + ".tmp", out)
    return out
