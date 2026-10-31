"""Synthetic green-screen figures for tests."""
from PIL import Image, ImageDraw

GREEN = (0, 177, 64)


def figure(path, size=(1000, 1000), bg=GREEN, cx=500, bottom=900, width=200, eyes_closed=False, through_bottom=False):
    """A 'toga' figure: white ellipse body with black outline, red belt, head; feet at `bottom`."""
    im = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(im)
    top = bottom - 600
    if through_bottom:
        bottom = size[1] + 50
    d.ellipse([cx - width // 2, top + 150, cx + width // 2, bottom], fill=(250, 250, 250), outline=(0, 0, 0), width=6)
    d.rectangle([cx - width // 2 + 10, top + 380, cx + width // 2 - 10, top + 410], fill=(200, 30, 30))
    d.ellipse([cx - 80, top, cx + 80, top + 160], fill=(230, 180, 140), outline=(0, 0, 0), width=6)
    if not eyes_closed:
        d.ellipse([cx - 40, top + 60, cx - 20, top + 80], fill=(0, 0, 0))
        d.ellipse([cx + 20, top + 60, cx + 40, top + 80], fill=(0, 0, 0))
    else:
        d.line([cx - 40, top + 70, cx - 20, top + 70], fill=(0, 0, 0), width=4)
        d.line([cx + 20, top + 70, cx + 40, top + 70], fill=(0, 0, 0), width=4)
    im.save(path)
    return path
