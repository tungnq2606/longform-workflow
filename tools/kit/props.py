"""Hand-drawn props in the same ink style as the stick figure.

Each prop is drawn around (0, 0) at roughly 160 px wide when s = 1.
Use prop(name, x, y, s, label=None).
"""
from build_visuals import ACC, ACC_L, GREY, INK, line, poly, rect, txt

W_ = "#fff"


def _house():
    return (poly([(-80, -10), (0, -85), (80, -10)], w=7, fill=ACC_L)
            + rect(-65, -10, 130, 95, W_, INK, 7, 4)
            + rect(-18, 30, 36, 55, ACC, INK, 5, 3)
            + rect(-52, 10, 26, 24, W_, INK, 4, 2) + rect(26, 10, 26, 24, W_, INK, 4, 2))


def _apartment():
    out = rect(-55, -90, 110, 180, W_, INK, 7, 4)
    for r in range(4):
        for c in range(2):
            out += rect(-38 + c * 46, -72 + r * 38, 30, 24, ACC_L if (r + c) % 3 == 0 else W_, INK, 4, 2)
    return out + rect(-14, 62, 28, 28, ACC, INK, 4, 2)


def _cash():
    out = ""
    for k in range(3):
        out += rect(-80 + k * 6, -40 + k * 14, 150, 70, "#e9f2df", INK, 6, 6)
    out += f'<circle cx="7" cy="23" r="20" fill="#fff" stroke="{INK}" stroke-width="5"/>'
    return out + txt(7, 35, "$", 32, "middle", INK, "bold")


def _coin():
    return (f'<circle cx="0" cy="0" r="48" fill="#f6d77a" stroke="{INK}" stroke-width="7"/>'
            + txt(0, 16, "$", 46, "middle", INK, "bold"))


def _car():
    return (poly([(-85, 20), (-85, -10), (-50, -15), (-25, -48), (35, -48), (60, -15), (88, -8), (88, 20), (-85, 20)], w=7, fill=ACC)
            + rect(-18, -40, 40, 24, W_, INK, 4, 3)
            + f'<circle cx="-48" cy="24" r="20" fill="#fff" stroke="{INK}" stroke-width="7"/>'
            + f'<circle cx="52" cy="24" r="20" fill="#fff" stroke="{INK}" stroke-width="7"/>')


def _groceries():
    return (line(-20, -60, 10, -95, 8, "#c79a4a") + line(10, -55, 40, -85, 8, "#6a9b4a")
            + poly([(-60, -45), (60, -45), (48, 75), (-48, 75), (-60, -45)], w=7, fill="#e6cfa3")
            + line(-30, -10, 30, -10, 4))


def _medical():
    return (rect(-60, -50, 120, 100, W_, INK, 7, 14)
            + rect(-12, -34, 24, 68, ACC, ACC, 0, 3) + rect(-34, -12, 68, 24, ACC, ACC, 0, 3))


def _receipt():
    zz = [(-55 + i * 11, 110 + (8 if i % 2 else 0)) for i in range(11)]
    out = poly([(-55, -110), (55, -110)] + [(55, 110)] + zz[::-1] + [(-55, 110), (-55, -110)], w=6, fill=W_)
    out += rect(-42, -92, 84, 18, ACC_L, ACC, 3, 3)
    for k in range(6):
        out += line(-40, -50 + k * 26, 40 - (k % 3) * 18, -50 + k * 26, 4)
    return out


def _calendar(label="2026"):
    return (rect(-60, -55, 120, 115, W_, INK, 7, 8) + rect(-60, -55, 120, 30, ACC, INK, 7, 8)
            + line(-30, -70, -30, -45, 7) + line(30, -70, 30, -45, 7)
            + txt(0, 30, label, 36, "middle", INK, "bold"))


def _calculator():
    out = rect(-55, -80, 110, 160, W_, INK, 7, 10) + rect(-40, -64, 80, 34, ACC_L, INK, 4, 4)
    for r in range(3):
        for c in range(3):
            out += rect(-38 + c * 28, -18 + r * 30, 20, 20, ACC if (r, c) == (2, 2) else W_, INK, 4, 3)
    return out


def _bank():
    out = poly([(-85, -30), (0, -85), (85, -30), (-85, -30)], w=7, fill=ACC_L)
    for k in range(4):
        out += rect(-62 + k * 38, -22, 18, 82, W_, INK, 5, 2)
    return out + rect(-85, 60, 170, 18, W_, INK, 6, 2)


def _bulb():
    return (f'<circle cx="0" cy="-20" r="45" fill="#f6d77a" stroke="{INK}" stroke-width="7"/>'
            + rect(-20, 25, 40, 34, W_, INK, 6, 4) + line(-14, 38, 14, 38, 4) + line(-14, 48, 14, 48, 4)
            + poly([(-10, -20), (0, -35), (10, -20)], w=4))


def _card():
    return (rect(-75, -48, 150, 96, ACC_L, INK, 7, 10) + rect(-75, -28, 150, 20, INK, INK, 0, 0)
            + rect(-55, 10, 36, 24, "#f6d77a", INK, 4, 3))


def _piggy():
    return (f'<ellipse cx="0" cy="0" rx="72" ry="52" fill="#f7c6c0" stroke="{INK}" stroke-width="7"/>'
            + f'<circle cx="32" cy="-12" r="5" fill="{INK}"/>' + rect(62, -12, 22, 26, "#f7c6c0", INK, 5, 6)
            + line(-14, -52, 14, -52, 7) + line(-40, 46, -40, 70, 8) + line(30, 46, 30, 70, 8))


def _city():
    return (rect(-80, -40, 40, 100, W_, INK, 6, 2) + rect(-38, -90, 46, 150, ACC_L, INK, 6, 2)
            + rect(10, -60, 36, 120, W_, INK, 6, 2) + rect(48, -20, 34, 80, W_, INK, 6, 2))


def _people():
    out = ""
    for k, dx in enumerate((-50, 0, 50)):
        out += f'<circle cx="{dx}" cy="-40" r="20" fill="#fff" stroke="{INK}" stroke-width="6"/>'
        out += line(dx, -20, dx, 40, 6) + line(dx, 40, dx - 18, 75, 6) + line(dx, 40, dx + 18, 75, 6)
    return out


def _scale():
    return (line(0, -70, 0, 70, 7) + line(-50, 70, 50, 70, 8) + line(-80, -55, 80, -55, 7)
            + poly([(-80, -55), (-105, 0), (-55, 0)], w=5) + poly([(80, -55), (55, 0), (105, 0)], w=5)
            + f'<path d="M-108 0 Q-80 26 -52 0" fill="{ACC_L}" stroke="{INK}" stroke-width="5"/>'
            + f'<path d="M52 0 Q80 26 108 0" fill="#e9f2df" stroke="{INK}" stroke-width="5"/>')


def _arrow_up():
    return poly([(-70, 50), (-20, 0), (10, 25), (65, -40)], ACC, 10) + poly([(30, -42), (68, -44), (64, -6)], ACC, 10)


def _question():
    return (f'<circle cx="0" cy="0" r="58" fill="{ACC_L}" stroke="{INK}" stroke-width="7"/>'
            + txt(0, 26, "?", 76, "middle", INK, "bold"))


def _bubble():
    return (rect(-90, -60, 180, 100, W_, INK, 7, 22) + poly([(-40, 40), (-55, 80), (-10, 40)], w=7, fill=W_)
            + line(-55, -25, 55, -25, 5) + line(-55, 2, 30, 2, 5))


def _docs():
    return (rect(-60, -80, 110, 150, W_, INK, 6, 6) + rect(-45, -65, 110, 150, W_, INK, 6, 6)
            + "".join(line(-28, -30 + k * 26, 45, -30 + k * 26, 4) for k in range(4))
            + txt(45, -38, "*", 60, "middle", ACC, "bold"))


def _tax():
    return (rect(-55, -75, 110, 150, W_, INK, 6, 6) + txt(0, -30, "TAX", 32, "middle", ACC, "bold")
            + "".join(line(-38, 0 + k * 22, 38, 0 + k * 22, 4) for k in range(3)))


def _wallet():
    return (rect(-75, -50, 150, 100, "#c79a4a", INK, 7, 14) + rect(20, -18, 55, 36, "#e0b874", INK, 6, 8)
            + f'<circle cx="38" cy="0" r="6" fill="{INK}"/>' + rect(-60, -66, 100, 24, "#e9f2df", INK, 5, 4))


def _cart():
    return (poly([(-90, -60), (-65, -60), (-40, 30), (60, 30), (78, -35), (-55, -35)], w=7, fill="#fff")
            + f'<circle cx="-30" cy="55" r="13" fill="#fff" stroke="{INK}" stroke-width="6"/>'
            + f'<circle cx="45" cy="55" r="13" fill="#fff" stroke="{INK}" stroke-width="6"/>'
            + rect(-30, -60, 40, 28, "#e6cfa3", INK, 5, 3) + rect(15, -55, 30, 22, ACC_L, INK, 5, 3))


def _pie(share=30):
    import math
    a = share / 100 * 2 * math.pi
    x, y = 70 * math.sin(a), -70 * math.cos(a)
    big = 1 if share > 50 else 0
    return (f'<circle cx="0" cy="0" r="70" fill="#fff" stroke="{INK}" stroke-width="7"/>'
            + f'<path d="M0 0 L0 -70 A70 70 0 {big} 1 {x:.1f} {y:.1f} Z" fill="{ACC}" stroke="{INK}" stroke-width="6"/>')


def _key():
    return (f'<circle cx="-45" cy="0" r="30" fill="#f6d77a" stroke="{INK}" stroke-width="7"/>'
            + line(-15, 0, 70, 0, 8) + line(50, 0, 50, 22, 8) + line(68, 0, 68, 18, 8))


ICONS = {"house": _house, "apartment": _apartment, "cash": _cash, "coin": _coin, "car": _car, "groceries": _groceries,
         "medical": _medical, "receipt": _receipt, "calculator": _calculator, "bank": _bank, "bulb": _bulb,
         "card": _card, "piggy": _piggy, "city": _city, "people": _people, "scale": _scale, "arrow_up": _arrow_up,
         "question": _question, "bubble": _bubble, "docs": _docs, "tax": _tax, "wallet": _wallet, "cart": _cart, "key": _key}


def prop(name, x, y, s=1.0, label=None, arg=None):
    if name == "calendar":
        body = _calendar(arg or "2026")
    elif name == "pie":
        body = _pie(arg or 30)
    else:
        body = ICONS[name]()
    out = f'<g transform="translate({x},{y}) scale({s})">{body}</g>'
    if label:
        out += txt(x, y + 125 * s, label, 28, "middle", GREY)
    return out


def houses_row(x, y, n=10, shaded=5, s=0.45, gap=95):
    out = ""
    for k in range(n):
        body = _house().replace(ACC_L, ACC) if k < shaded else _house()
        out += f'<g transform="translate({x + k * gap},{y}) scale({s})">{body}</g>'
    return out
