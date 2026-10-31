"""Scene kit (v2 style): helpers to draw one frame as a small scene.

Import in a video's visuals/scenes.py:  from scene_kit import *
Output size comes from env OUT_W (default 1920); drawings use a 1920x1080 space.
"""
import math
import os

import build_visuals as bv
from build_visuals import ACC, ACC_L, GREY, INK, line, poly, rect, txt
from storyboard import figure
from props import houses_row, prop

OUT_W = int(os.environ.get("OUT_W", "1920"))
OUT_H = OUT_W * 9 // 16
GREEN, GOLD, SKY = "#e9f2df", "#f6d77a", "#9fb3c4"


# ---------------------------------------------------------------- helpers
def page(body, bg, num):
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;background:{bg}}}svg{{display:block;font-family:{bv.FONT}}}</style></head><body>
<svg width="{OUT_W}" height="{OUT_H}" viewBox="0 0 1920 1080" xmlns="http://www.w3.org/2000/svg"><defs><filter id="rough" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves="2" seed="{num}" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="3.5"/></filter></defs>
<rect width="1920" height="1080" fill="{bg}"/><g filter="url(#rough)">{body}</g></svg></body></html>"""


def F(x, y, s=1.0, pose="neutral", brows="flat", eyes="center", mouth="flat", flip=False):
    g = figure(x, y, s, pose, brows, eyes, mouth)
    return f'<g transform="translate({2 * x},0) scale(-1,1)">{g}</g>' if flip else g


def ground(y=930, c=SKY):
    return line(40, y, 1880, y, 5, c)


def T(x, y, s, size=40, anchor="middle", fill=INK, bold=False):
    return txt(x, y, s, size, anchor, fill, "bold" if bold else "normal")


def bubble(x, y, w, h, text, size=38, think=False, tail="left"):
    out = rect(x, y, w, h, "#fff", INK, 6, 40)
    tx = x + 70 if tail == "left" else x + w - 70
    if think:
        out += f'<circle cx="{tx}" cy="{y + h + 32}" r="17" fill="#fff" stroke="{INK}" stroke-width="5"/>'
        out += f'<circle cx="{tx - 28 if tail == "left" else tx + 28}" cy="{y + h + 68}" r="10" fill="#fff" stroke="{INK}" stroke-width="5"/>'
    else:
        d = -1 if tail == "left" else 1
        out += poly([(tx - 25, y + h - 3), (tx + d * 35, y + h + 55), (tx + 25, y + h - 3)], w=6, fill="#fff")
    lines_ = text.split("|")
    y0 = y + h / 2 - (len(lines_) - 1) * (size + 10) / 2 + size * 0.35
    for i, t_ in enumerate(lines_):
        out += T(x + w / 2, y0 + i * (size + 10), t_, size)
    return out


def think_icons(x, y, w, h, icons):
    out = bubble(x, y, w, h, "", think=True)
    step = w / (len(icons) + 1)
    for i, n in enumerate(icons):
        out += prop(n, x + step * (i + 1), y + h / 2 + 5, 0.62)
    return out


def big(x, y, s, size=110, fill=ACC):
    return T(x, y, s, size, "middle", fill, True)


def note(x, y, text, w=330, rot=-3, size=30):
    lines_ = text.split("|")
    h = 40 + len(lines_) * (size + 10)
    out = f'<g transform="rotate({rot} {x} {y})">' + rect(x - w / 2, y - h / 2, w, h, "#fff3b0", INK, 4, 4)
    for i, t_ in enumerate(lines_):
        out += T(x, y - h / 2 + 30 + size * 0.8 + i * (size + 10), t_, size)
    return out + "</g>"


def stamp(x, y, text, rot=-10, size=52, c=ACC):
    w = len(text) * size * 0.62 + 50
    return (f'<g transform="rotate({rot} {x} {y})">' + rect(x - w / 2, y - size * 0.9, w, size * 1.4, "none", c, 7, 8)
            + T(x, y + size * 0.3, text, size, "middle", c, True) + "</g>")


def check(x, y, w=620, h=260, amount="$60,320", sub="a year, before tax"):
    return (rect(x, y, w, h, GREEN, INK, 7, 12) + T(x + 30, y + 55, "PAY TO: our median worker", 30, "start", GREY)
            + T(x + w / 2, y + 150, amount, 84, "middle", INK, True) + T(x + w / 2, y + 210, sub, 32, "middle", GREY)
            + line(x + 30, y + h - 30, x + w - 30, y + h - 30, 3, GREY))


def bill(x, y, w=420, h=300, title="RENT + UTILITIES", amount="$1,487", sub="a month (2024 median)"):
    return (rect(x, y, w, h, "#fff", INK, 7, 10) + rect(x, y, w, 60, ACC, INK, 7, 10)
            + T(x + w / 2, y + 42, title, 32, "middle", "#fff", True) + T(x + w / 2, y + 170, amount, 76, "middle", INK, True)
            + T(x + w / 2, y + 230, sub, 28, "middle", GREY))


def strip(x, y, w, cuts, label, amount, h=150):
    """Paycheck strip; cuts = [(share, colour, text)] taken from the right end."""
    out = rect(x, y, w, h, GREEN, INK, 7, 10) + T(x + 30, y + 55, label, 30, "start", GREY) + T(x + 30, y + 115, amount, 48, "start", INK, True)
    right = x + w
    for share, col, t_ in cuts:
        cw = w * share
        right -= cw
        out += rect(right, y, cw, h, col, ACC, 6, 8) + line(right, y - 30, right, y + h + 30, 5, INK, "12 9")
        parts = t_.split("|")
        if cw >= 220:
            for i, part in enumerate(parts):
                out += T(right + cw / 2, y + h / 2 + 12 + (i - (len(parts) - 1) / 2) * 36, part, 30, "middle", ACC, True)
        else:  # narrow slice: label below, staggered
            ly = y + h + 60 + (len(out) % 2) * 0
            for i, part in enumerate(parts):
                out += T(right + cw / 2, y + h + 55 + i * 36 + (90 if len(cuts) > 1 and (right - x) / w > 0.9 else 0), part, 30, "middle", ACC, True)
    return out


def scissors(x, y, s=1.0):
    return (f'<g transform="translate({x},{y}) scale({s}) rotate(-20)">'
            + f'<circle cx="-40" cy="30" r="22" fill="none" stroke="{INK}" stroke-width="7"/>'
            + f'<circle cx="-40" cy="-30" r="22" fill="none" stroke="{INK}" stroke-width="7"/>'
            + line(-22, 20, 70, -18, 7) + line(-22, -20, 70, 18, 7) + "</g>")


def runner(x, y, s, label, color, mouth="flat", sweat=False):
    g = [f'<g transform="translate({x},{y}) scale({s})">',
         f'<circle cx="0" cy="0" r="62" fill="#fff" stroke="{INK}" stroke-width="7"/>',
         f'<circle cx="14" cy="-6" r="6" fill="{INK}"/><circle cx="40" cy="-6" r="6" fill="{INK}"/>',
         line(4, -34, 26, -40, 6) + line(32, -40, 52, -32, 6),
         poly({"smile": [(10, 26), (30, 36), (48, 26)], "frown": [(12, 36), (30, 28), (46, 36)]}.get(mouth, [(12, 32), (46, 32)]), w=6),
         line(-10, 62, -40, 210, 7),
         poly([(-18, 95), (40, 120), (70, 85)], w=7) + poly([(-18, 95), (-70, 135), (-95, 110)], w=7),
         poly([(-40, 210), (20, 260), (10, 330)], w=7) + poly([(-40, 210), (-90, 270), (-150, 280)], w=7),
         f'<g transform="rotate(14 -25 132)">' + rect(-75, 108, 100, 48, color, INK, 5, 6)
         + T(-25, 143, label, 28, "middle", "#fff" if color == ACC else INK, True) + "</g>"]
    for k in range(3):
        g.append(line(-175 - k * 10, 60 + k * 50, -115 - k * 10, 60 + k * 50, 5, SKY))
    if sweat:
        g.append(f'<path d="M-62 -40 q-10 18 0 26 q10 -8 0 -26" fill="#7fb6e6" stroke="{INK}" stroke-width="3"/>')
    g.append("</g>")
    return "".join(g)


def track(years=("2019", "2022", "2024", "2026"), shade=None, y=900):
    out = ground(y)
    xs = [220 + k * 500 for k in range(len(years))]
    if shade is not None:
        a, b = shade
        out += f'<rect x="{xs[a]}" y="{y - 380}" width="{xs[b] - xs[a]}" height="380" fill="{ACC_L}" opacity="0.65"/>'
    for x, yr in zip(xs, years):
        out += line(x, y - 20, x, y + 20, 6) + T(x, y + 62, yr, 34, "middle", GREY)
    return out


def pie(x, y, r, shares, labels=None):
    out, a0 = f'<circle cx="{x}" cy="{y}" r="{r}" fill="#fff" stroke="{INK}" stroke-width="7"/>', 0.0
    cols = [ACC, "#f2a679", GOLD, "#a8cfa0"]
    for i, sh in enumerate(shares):
        a1 = a0 + sh / 100 * 2 * math.pi
        x0, y0 = x + r * math.sin(a0), y - r * math.cos(a0)
        x1, y1 = x + r * math.sin(a1), y - r * math.cos(a1)
        big_ = 1 if sh > 50 else 0
        out += f'<path d="M{x} {y} L{x0:.1f} {y0:.1f} A{r} {r} 0 {big_} 1 {x1:.1f} {y1:.1f} Z" fill="{cols[i % 4]}" stroke="{INK}" stroke-width="6"/>'
        if labels:
            am = (a0 + a1) / 2
            out += T(x + (r + 70) * math.sin(am), y - (r + 70) * math.cos(am) + 12, labels[i], 32, "middle", INK, True)
        a0 = a1
    return out


def signpost(x, y, a, b):
    return (line(x, y, x, y + 330, 9) + poly([(x - 10, y + 10), (x + 430, y + 10), (x + 480, y + 55), (x + 430, y + 100), (x - 10, y + 100)], w=7, fill="#fff")
            + T(x + 220, y + 70, a, 34, "middle", INK, True)
            + poly([(x + 10, y + 140), (x - 430, y + 140), (x - 480, y + 185), (x - 430, y + 230), (x + 10, y + 230)], w=7, fill=ACC_L)
            + T(x - 220, y + 200, b, 34, "middle", INK, True))


def chalkboard(x, y, w, h, text, size=60):
    return (rect(x, y, w, h, "#2f4a3a", "#6b4f2c", 14, 6) + T(x + w / 2, y + h / 2 + size * 0.35, text, size, "middle", "#f4f1e6", True)
            + line(x + 40, y + h + 10, x + w - 40, y + h + 10, 6, "#6b4f2c"))


def gavel(x, y, s=1.0):
    return (f'<g transform="translate({x},{y}) scale({s}) rotate(-30)">' + rect(-60, -30, 120, 60, "#c79a4a", INK, 6, 8)
            + rect(-8, 30, 16, 120, "#c79a4a", INK, 5, 4) + "</g>")


def table(x, y, w):
    return rect(x, y, w, 24, "#c79a4a", INK, 6, 4) + line(x + 30, y + 24, x + 30, y + 150, 7) + line(x + w - 30, y + 24, x + w - 30, y + 150, 7)


def stairs(x, y, n=3, step=140, rise=80):
    pts = [(x, y)]
    for k in range(n):
        pts += [(x + k * step, y - (k + 1) * rise), (x + (k + 1) * step, y - (k + 1) * rise)]
    pts.append((x + n * step, y))
    return poly(pts, w=7, fill="#fff")


def tightrope(x0, x1, y, label):
    return (line(x0, y - 220, x0, y + 160, 9) + line(x1, y - 220, x1, y + 160, 9) + line(x0, y - 200, x1, y - 200, 5)
            + T(x1 + 20, y - 210, label, 34, "start", ACC, True))


def mini_chart(x0, y0, w, h, pay_series, rent_series, shade=(2022, 2024)):
    """Two indexed lines (first year = 100). Series are {year: value}."""
    years = sorted(pay_series)
    pay = {k: pay_series[k] / pay_series[years[0]] * 100 for k in years}
    rent = {k: rent_series[k] / rent_series[years[0]] * 100 for k in years}
    chart, xs, ys = bv.line_chart([pay, rent], x0, y0, w, h, 100, 140, years, [INK, ACC], [f"pay {pay[2026]:.0f}", f"rent {rent[2026]:.0f}"], shade)
    return chart


def crowd_line(x, y, heights, gap=110, mark=None):
    out = ""
    for i, hgt in enumerate(heights):
        s = 0.32 + hgt * 0.06
        out += F(x + i * gap, y - 120 * s, s, "neutral", "flat", "center", "flat")
    if mark is not None:
        mx = x + mark * gap
        out += line(mx, y + 30, mx, y + 90, 6, ACC) + T(mx, y + 130, "median", 32, "middle", ACC, True)
    return out


def card_scene(num, chapters):
    """Chapter card shown in silence before voice block `num`; chapters = {num: title}."""
    idx = sorted(chapters).index(num) + 1
    title = chapters[num]
    size = min(92, int(1050 / (len(title) * 0.56)))
    return (ground(930) + F(380, 470, 1.4, "present", "raise", "right", "smirk")
            + T(760, 470, f"Part {idx}", 44, "start", GREY) + T(760, 570, title, size, "start", INK, True)
            + line(760, 600, 760 + min(1060, int(len(title) * size * 0.56)), 600, 10, ACC))


