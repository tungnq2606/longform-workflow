"""AI upscale of agy images (agy returns ~1376x768 and has no resolution option).

Real-ESRGAN ncnn-vulkan v0.2.5.0 (BSD-3, offline, Mac GPU) with the realesr-animevideov3 model: the owner picked it
on 2026-10-31 (sharp ink lines, colours closest to the original). Binary in tools/upscale/vendor/ (gitignored).

  python -m tools.longform.upscale SRC DST [--bg | --scale 2]
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image

from tools.longform import paths

VENDOR = os.path.join(paths.WS, "tools", "upscale", "vendor", "realesrgan")
BIN = os.path.join(VENDOR, "realesrgan-ncnn-vulkan")
MODEL = "realesr-animevideov3"
BG_SIZE = (2816, 1584)  # 1440p + 10% room for camera push-in and pan


def command(src, dst, scale):
    return [BIN, "-i", src, "-o", dst, "-n", MODEL, "-s", str(scale), "-m", os.path.join(VENDOR, "models")]


def cover_box(src_size, size):
    """Resize size and crop box that cover `size` from `src_size` without distortion (centre crop)."""
    sw, sh = src_size
    w, h = size
    s = max(w / sw, h / sh)
    rw, rh = round(sw * s), round(sh * s)
    x, y = (rw - w) // 2, (rh - h) // 2
    return (rw, rh), (x, y, x + w, y + h)


def upscale(src, dst, size=None, scale=2):
    """4x with Real-ESRGAN, then Lanczos down to `size` (cover + centre crop) or to `scale` x the source size."""
    sw, sh = Image.open(src).size
    with tempfile.TemporaryDirectory() as tmp:
        big = os.path.join(tmp, "x4.png")
        p = subprocess.run(command(os.path.abspath(src), big, 4), capture_output=True, text=True)
        if p.returncode != 0 or not os.path.exists(big):
            raise RuntimeError("Real-ESRGAN failed: %s" % (p.stderr or p.stdout)[-300:])
        im = Image.open(big).convert("RGB")
        if size:
            rs, box = cover_box(im.size, size)
            im = im.resize(rs, Image.LANCZOS).crop(box)
        else:
            im = im.resize((sw * scale, sh * scale), Image.LANCZOS)
        im.save(dst)
    return im.size


if __name__ == "__main__":
    a = sys.argv[1:]
    print(upscale(a[0], a[1], size=BG_SIZE if "--bg" in a else None, scale=int(a[a.index("--scale") + 1]) if "--scale" in a else 2))
