#!/usr/bin/env python3
"""Build Video 1 frames in one hand-drawn stick-figure style.

Output: html/*.html (editable), png/sNN_*.png (1920x1080 frames),
sprites/*.png (transparent stick-figure poses). Rendering uses headless Edge.
All numbers come from day1-script/sources_log.csv (see DATA below).

Run:  python3 build_visuals.py
"""
import html as H
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EDGE = "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"

INK, PAPER, ACC, ACC_L, GREY = "#1b1b1b", "#FAF7F0", "#D9480F", "#FBD9C6", "#8a8a85"
FONT = "'PatrickHand', cursive"  # SIL OFL 1.1, see fonts/LICENSE_PatrickHand.txt
FONT_FACE = "@font-face{font-family:'PatrickHand';src:url('file://%s/fonts/PatrickHand-Regular.ttf')}" % os.path.dirname(os.path.abspath(__file__))
W, Hh = 1920, 1080

# ---- DATA (values read from sources; exact figures stay on screen) ----
PAY_Q2 = {2019: 914, 2020: 1008, 2021: 996, 2022: 1048, 2023: 1108, 2024: 1151, 2025: 1205, 2026: 1258}
RENT_JUN = {2019: 330.919, 2020: 341.524, 2021: 348.070, 2022: 368.216, 2023: 398.949, 2024: 419.223, 2025: 435.033, 2026: 447.397}
INCOME_AT = {2019: 67887, 2020: 73273, 2021: 78214, 2022: 80769, 2023: 84939}
SPEND = {2019: 57128, 2020: 57644, 2021: 63905, 2022: 67884, 2023: 71867}
CE2024 = [("Housing", 26380), ("Transportation", 12802), ("Food", 9630), ("Healthcare", 3825)]
CE_TOTAL_2024 = 74475
GROWTH_19_24 = [("Total spending", 30.4), ("Food", 30.7), ("Housing", 28.7), ("Transportation", 24.3), ("Healthcare", 21.0)]


def e(s):
    return H.escape(str(s), quote=True)


def txt(x, y, s, size=40, anchor="start", fill=INK, weight="normal", style=""):
    size = round(size * 1.15)  # Patrick Hand runs narrower than the old font
    return (f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
            f'font-weight="{weight}" {style}>{e(s)}</text>')


def line(x1, y1, x2, y2, w=6, c=INK, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="{w}" stroke-linecap="round"{d}/>'


def rect(x, y, w, h, fill="none", c=INK, sw=6, r=10):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{c}" stroke-width="{sw}"/>'


def poly(points, c=INK, w=7, fill="none"):
    p = " ".join(f"{x},{y}" for x, y in points)
    return f'<polyline points="{p}" fill="{fill}" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'


# ---------- the one character ----------
def stick(x, y, s=1.0, pose="neutral", label=None):
    """Head centre at (x, y). Big head, dot eyes, expressive eyebrows."""
    arms = {
        "neutral": [((-8, 105), (-70, 200)), ((8, 105), (70, 200))],
        "brow": [((-8, 105), (-70, 200)), ((8, 105), (70, 200))],
        "paper": [((-8, 105), (-70, 200)), ((8, 105), (95, 150))],
        "point": [((-8, 105), (-70, 200)), ((8, 105), (210, 85))],
        "cross": [((-8, 110), (45, 175)), ((8, 110), (-45, 175))],
        "lens": [((-8, 105), (-70, 200)), ((8, 105), (115, 70))],
    }[pose]
    brows = (((-44, -38), (-14, -38)), ((14, -38), (44, -38)))
    if pose in ("brow", "lens"):
        brows = (((-44, -38), (-14, -38)), ((14, -34), (44, -56)))
    if pose == "cross":
        brows = (((-44, -44), (-14, -34)), ((14, -34), (44, -44)))
    g = [f'<g transform="translate({x},{y}) scale({s})">']
    g.append('<circle cx="0" cy="0" r="72" fill="#fff" stroke="%s" stroke-width="7"/>' % INK)
    g.append('<circle cx="-24" cy="-6" r="6" fill="%s"/><circle cx="24" cy="-6" r="6" fill="%s"/>' % (INK, INK))
    for (a, b) in brows:
        g.append(line(a[0], a[1], b[0], b[1], 7))
    g.append(poly([(-18, 32), (0, 36), (18, 32)], w=6))
    g.append(line(0, 72, 0, 235, 7))
    for (a, b) in arms:
        g.append(line(a[0], a[1], b[0], b[1], 7))
    g.append(line(0, 235, -55, 340, 7))
    g.append(line(0, 235, 55, 340, 7))
    if pose == "paper":
        g.append(rect(60, 70, 100, 130, "#fff", INK, 5, 6))
        g.append(line(76, 100, 144, 100, 4) + line(76, 124, 144, 124, 4) + line(76, 148, 120, 148, 4))
    if pose == "lens":
        g.append('<circle cx="140" cy="40" r="42" fill="none" stroke="%s" stroke-width="7"/>' % INK)
        g.append(line(115, 70, 125, 62, 7))
    if label:
        g.append(txt(0, 392, label, 26, "middle", GREY))
    g.append("</g>")
    return "\n".join(g)


def footer(source, width=150):
    if not source:
        return ""
    words, lines, cur = source.split(" "), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    y0 = 1038 - 30 * (len(lines) - 1)
    return "\n".join(txt(90, y0 + 30 * i, l, 24, "start", GREY) for i, l in enumerate(lines))


def scene(title, body, source, num):
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;background:{PAPER};}}
svg{{display:block;font-family:{FONT};}}
</style></head><body>
<svg width="{W}" height="{Hh}" viewBox="0 0 {W} {Hh}" xmlns="http://www.w3.org/2000/svg">
<defs><filter id="rough" x="-2%" y="-2%" width="104%" height="104%">
<feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves="2" seed="{num}" result="n"/>
<feDisplacementMap in="SourceGraphic" in2="n" scale="3.5"/></filter></defs>
<rect width="{W}" height="{Hh}" fill="{PAPER}"/>
<g filter="url(#rough)">
{(txt(90, 120, title, 64, "start", INK, "bold") + line(90, 146, 90 + min(1700, len(title) * 34), 146, 8, ACC)) if title else ""}
{body}
</g>
{footer(source)}
</svg></body></html>"""


def chip(x, y, w, h, lines, big=None, accent=False):
    out = [rect(x, y, w, h, ACC_L if accent else "#fff", ACC if accent else INK, 5, 14)]
    ty = y + 52
    if big:
        out.append(txt(x + w / 2, ty + 14, big, 76, "middle", ACC if accent else INK, "bold"))
        ty += 82
    for l in lines:
        out.append(txt(x + w / 2, ty, l, 30, "middle", INK))
        ty += 40
    return "\n".join(out)


# ---------- scenes ----------
def s01():
    b = [stick(290, 330, 1.5, "paper")]
    b.append(txt(290, 905, "median worker", 28, "middle", GREY))
    b.append(txt(290, 940, "(illustration, not a real person)", 26, "middle", GREY))
    b.append(txt(620, 330, "$60,320 a year before tax", 44, "start", INK, "bold"))
    b.append(txt(620, 385, "$1,487 a month rent + utilities (2024 median)", 36))
    # bar: share of pay
    bx, by, bw = 620, 470, 1000
    b.append(rect(bx, by, bw, 70, "#fff", INK, 6, 10))
    b.append(f'<rect x="{bx}" y="{by}" width="{bw * 0.296}" height="70" rx="8" fill="{ACC}"/>')
    b.append(line(bx + bw * 0.30, by - 25, bx + bw * 0.30, by + 95, 7, INK, "10 8"))
    b.append(txt(bx + bw * 0.30, by - 36, "HUD line: 30%", 30, "middle", INK, "bold"))
    b.append(txt(bx + bw * 0.30 + 24, by + 50, "rent = 29.6% of pay", 36, "start", ACC, "bold"))
    b.append(txt(620, 640, "2026 pay, 2024 rent. One salary against a national rent: a rough benchmark.", 30, "start", GREY))
    b.append(chip(620, 700, 1180, 190,
                  ["Different group, so it does not grade our worker:", "renter households of all ages, ACS 2024, over the line:", "51.8% of households with computed burden (48.2% of all)"],
                  None, True))
    return scene("Rent vs. a median full-time paycheck", "\n".join(b),
                 "BLS Usual Weekly Earnings Q2 2026 (ages 25-34); Census ACS 2024 B25064, B25070 (via Census Reporter); HUD 30% threshold (via CRS); channel calculation", 1)


def s02():
    b = [stick(260, 430, 1.4, "brow")]
    rows = [
        ("Pay", "$1,160 a week  x 52  =  $60,320 a year"),
        ("Rent + utilities", "$1,487 a month  x 12  =  $17,844 a year"),
        ("Share", "$17,844  ÷  $60,320  =  29.6%  (before tax)"),
    ]
    y = 300
    for i, (k, v) in enumerate(rows):
        b.append(txt(520, y, k, 34, "start", GREY))
        b.append(txt(520, y + 52, v, 50, "start", ACC if i == 2 else INK, "bold"))
        y += 150
    b.append(chip(520, 770, 400, 190, ["if rent rose with the", "official rent index"], "~31.6%", True))
    b.append(chip(960, 770, 400, 190, ["ages 16-24", "(often shared housing)"], "42.6%"))
    b.append(chip(1400, 770, 400, 190, ["all full-time", "workers"], "27.4%"))
    return scene("The math", "\n".join(b),
                 "BLS Q2 2026 table 3 ($1,160; $806; $1,251); Census ACS 2024 B25064 $1,487; FRED CUSR0000SEHA (estimate assumes national rent moves like the index); rough benchmark", 2)


def s03():
    b = [stick(260, 430, 1.4, "paper")]
    rows = [("Pay before tax", "$60,320", INK), ("Federal income tax", "- $5,058.40", ACC), ("Payroll tax (7.65%)", "- $4,614.48", ACC),
            ("Take-home pay", "$50,647  =  $4,221 a month", INK), ("Rent + utilities", "- $1,487 a month", ACC), ("Left (before state tax, premiums)", "$2,734 a month", INK)]
    y = 270
    for k, v, c in rows:
        b.append(txt(520, y, k, 36, "start", GREY))
        b.append(txt(1840, y, v, 40, "end", c, "bold"))
        b.append(line(520, y + 14, 1840, y + 14, 3, "#cfcbbf"))
        y += 80
    b.append(txt(520, y + 20, "Rent = 35.2% of take-home pay. Not HUD's measure.", 42, "start", ACC, "bold"))
    b.append(rect(520, y + 60, 1320, 150, ACC_L, ACC, 4, 12))
    b.append(txt(550, y + 105, "Assumptions: single filer, one job, standard deduction $16,100,", 28))
    b.append(txt(550, y + 142, "10% to $12,400 and 12% above; federal income tax and payroll tax only;", 28))
    b.append(txt(550, y + 179, "no state or local tax, no pre-tax deductions.", 28))
    return scene("Take-home pay", "\n".join(b),
                 "IRS Rev. Proc. 2025-32 (tax year 2026); IRS Topic 751 (6.2% + 1.45%); channel calculation", 3)


def s04():
    b = [stick(260, 430, 1.4, "brow")]
    b.append(txt(1100, 300, "(rent + utilities)", 56, "middle", INK, "bold"))
    b.append(line(640, 330, 1560, 330, 8))
    b.append(txt(1100, 410, "household income before tax", 56, "middle", INK, "bold"))
    b.append(txt(1100, 500, "over 30%  =  \"cost burdened\" (HUD)", 46, "middle", ACC, "bold"))
    b.append(txt(560, 640, "It ignores:", 40, "start", GREY))
    for i, t in enumerate(["debt", "savings", "city prices", "how many people share the home"]):
        b.append(txt(600, 700 + i * 60, "x  " + t, 36))
    b.append(chip(1290, 580, 530, 290, ["A household under the line", "can still be stretched.", "One over it can be fine.", "A screening rule, not a verdict."], None, True))
    return scene("Why 30 percent?", "\n".join(b),
                 "HUD cost-burden threshold as described in CRS reports and state housing analyses; gross rent includes utilities", 4)


def s05():
    b = [stick(200, 400, 1.2, "neutral")]
    x0, y0, maxw = 640, 260, 880
    maxv = CE2024[0][1]
    y = y0
    for name, v in CE2024:
        w = maxw * v / maxv
        b.append(txt(x0 - 20, y + 52, name, 36, "end", INK, "bold"))
        b.append(f'<rect x="{x0}" y="{y}" width="{w}" height="78" rx="8" fill="{ACC if name == "Housing" else "#fff"}" stroke="{INK}" stroke-width="6"/>')
        b.append(txt(x0 + w + 20, y + 54, f"${v:,}  ({v / CE_TOTAL_2024 * 100:.1f}%)", 36, "start", INK, "bold"))
        y += 130
    b.append(txt(x0, y + 20, f"Total average spending: ${CE_TOTAL_2024:,}.  These four lines: 70.7%.", 38, "start", ACC, "bold"))
    b.append(txt(x0, y + 75, "What households spent, not what they need. Owners and renters both included.", 30, "start", GREY))
    return scene("Where a household aged 25-34 spent in 2024", "\n".join(b),
                 "BLS Consumer Expenditure Survey, ages 25-34, via FRED; 2024; averages in current dollars; other categories not shown", 5)


def line_chart(series, x0, y0, w, h, ymin, ymax, years, colors, labels, shade=None, fmt=lambda v: f"{v:.0f}"):
    out = []
    xs = {yr: x0 + w * (yr - years[0]) / (years[-1] - years[0]) for yr in years}
    ys = lambda v: y0 + h - h * (v - ymin) / (ymax - ymin)
    if shade:
        out.append(f'<rect x="{xs[shade[0]]}" y="{y0}" width="{xs[shade[1]] - xs[shade[0]]}" height="{h}" fill="{ACC_L}" opacity="0.8"/>')
    out.append(line(x0, y0 + h, x0 + w, y0 + h, 6))
    out.append(line(x0, y0, x0, y0 + h, 6))
    for yr in years:
        out.append(txt(xs[yr], y0 + h + 40, yr, 28, "middle", GREY))
    for tick in range(int(ymin), int(ymax) + 1, int((ymax - ymin) / 4)):
        out.append(line(x0 - 8, ys(tick), x0, ys(tick), 4))
        out.append(txt(x0 - 16, ys(tick) + 10, fmt(tick), 26, "end", GREY))
    for s, c, lab in zip(series, colors, labels):
        pts = [(xs[yr], ys(s[yr])) for yr in years if yr in s]
        out.append(poly(pts, c, 9))
        for p in pts:
            out.append(f'<circle cx="{p[0]}" cy="{p[1]}" r="8" fill="{c}"/>')
        last = pts[-1]
        out.append(txt(last[0] + 18, last[1] + 8, lab, 30, "start", c, "bold"))
    return "\n".join(out), xs, ys


def s06():
    years = list(range(2019, 2027))
    pay = {y: PAY_Q2[y] / PAY_Q2[2019] * 100 for y in years}
    rent = {y: RENT_JUN[y] / RENT_JUN[2019] * 100 for y in years}
    b = [stick(170, 430, 1.0, "lens")]
    chart, xs, ys = line_chart([pay, rent], 480, 250, 1080, 500, 100, 140, years, [INK, ACC],
                               [f"pay {pay[2026]:.0f}", f"rent {rent[2026]:.0f}"], (2022, 2024))
    b.append(chart)
    b.append(txt(480 + 1080 * 2.5 / 7, 238, "rent ran ahead", 32, "middle", ACC, "bold"))
    b.append(txt(480, 860, "Index, 2019 = 100. Pay ahead 2019-22, rent ahead 2022-24, pay ahead 2024-26.", 32, "start", INK))
    cols = [("2019-22", "+14.7", "+11.3"), ("2022-24", "+9.8", "+13.9"), ("2024-26", "+9.3", "+6.7"), ("year to mid-2026", "+4.4", "+2.8")]
    x = 480
    for k, p_, r_ in cols:
        b.append(txt(x, 925, k, 28, "start", INK, "bold"))
        b.append(txt(x, 962, f"pay {p_}%  rent {r_}%", 26, "start", GREY))
        x += 340
    return scene("Pay vs. rent, 2019-2026", "\n".join(b),
                 "FRED LES1252881500Q (median weekly earnings, all full-time wage and salary workers 16+, seasonally adjusted, Q2) and CUSR0000SEHA (CPI rent of primary residence, June); current dollars", 6)


def s07():
    b = [stick(260, 430, 1.4, "cross")]
    b.append(chip(640, 280, 480, 270, ["median weekly pay,", "all full-time workers"], "+4.6%", False))
    b.append(chip(1200, 280, 480, 270, ["consumer prices,", "all items"], "+3.9%", True))
    b.append(txt(640, 650, "Year to mid-2026. A different series from the chart", 34, "start", INK))
    b.append(txt(640, 700, "(the chart's 4.4% is seasonally adjusted).", 34, "start", INK))
    b.append(txt(640, 765, "Not rent, and not ages 25-34.", 36, "start", ACC, "bold"))
    return scene("For scale: pay and prices, year to mid-2026", "\n".join(b),
                 "BLS Usual Weekly Earnings Q2 2026 news release (headline, not seasonally adjusted); CPI-U", 7)


def s08():
    years = [2019, 2020, 2021, 2022, 2023]
    b = [stick(170, 430, 1.0, "neutral")]
    chart, xs, ys = line_chart([INCOME_AT, SPEND], 430, 250, 600, 480, 50000, 90000, years, [INK, ACC],
                               ["", ""], None, lambda v: f"${v // 1000}K")
    b.append(chart)
    b.append(txt(600, ys(INCOME_AT[2021]) - 70, "income after taxes", 30, "start", INK, "bold"))
    b.append(txt(640, ys(SPEND[2022]) + 80, "spending", 30, "start", ACC, "bold"))
    b.append(txt(430, 840, "2019-23: income after taxes +25.1%, spending +25.8%", 34, "start", INK, "bold"))
    b.append(txt(430, 890, "Spending share: 84.2% (2019), 84.6% (2023). Income series ends in 2023.", 28, "start", GREY))
    b.append(txt(1180, 262, "Spending, 2019 to 2024:", 30, "start", GREY))
    y = 300
    for name, g in GROWTH_19_24:
        w = 300 * g / 32
        b.append(txt(1400, y + 36, name, 26, "end", INK))
        b.append(f'<rect x="1415" y="{y}" width="{w}" height="50" rx="6" fill="#fff" stroke="{INK}" stroke-width="5"/>')
        b.append(txt(1415 + w + 12, y + 36, f"+{g:.1f}%", 28, "start", ACC, "bold"))
        y += 90
    return scene("Household budgets, ages 25-34", "\n".join(b),
                 "BLS Consumer Expenditure Survey, ages 25-34, via FRED (CXUINCAFTAXLB0403M, CXUTOTALEXPLB0403M and category series); current dollars; averages including owners", 8)


def s09():
    b = [stick(260, 430, 1.4, "lens")]
    notes = [("1", "A median can move when the mix of workers changes."),
             ("2", "The rent index follows what current tenants pay,|not the price on a new listing."),
             ("3", "Averages include owners and big spenders.")]
    y = 330
    for n, t in notes:
        b.append(f'<circle cx="640" cy="{y - 12}" r="30" fill="{ACC}" stroke="{INK}" stroke-width="5"/>')
        b.append(txt(640, y, n, 36, "middle", "#fff", "bold"))
        for j, part in enumerate(t.split("|")):
            b.append(txt(700, y + 48 * j, part, 40, "start", INK))
        y += 150
    return scene("Three footnotes", "\n".join(b), "BLS CPI factsheet on rent; general statistical caution", 9)


def s10():
    b = [stick(260, 430, 1.4, "neutral")]
    b.append(txt(640, 290, "Check your own number:", 44, "start", GREY))
    b.append(txt(640, 360, "(your rent + utilities)  ÷  (household income before tax)", 42, "start", INK, "bold"))
    b.append(txt(640, 420, "Over 30%: above HUD's line. Nothing more.", 38, "start", ACC, "bold"))
    b.append(txt(640, 520, "Sources and checks:", 34, "start", GREY))
    src = ["BLS Usual Weekly Earnings, Q2 2026, read at bls.gov",
           "BLS Consumer Expenditure Survey and FRED series (read via FRED)",
           "IRS Rev. Proc. 2025-32; IRS Topic 751 (read at irs.gov)",
           "Census ACS 2024 B25064, B25070 (via Census Reporter copy of ACS data)",
           "HUD 30% threshold (secondary: CRS and state analyses)"]
    for i, t in enumerate(src):
        b.append(txt(670, 575 + i * 46, t, 28, "start", INK))
    b.append(rect(640, 820, 1180, 130, ACC_L, ACC, 4, 12))
    b.append(txt(670, 865, "Not advice on what to buy, save or invest in.", 34, "start", INK, "bold"))
    b.append(txt(670, 915, "Spot a mistake? Tell us in the comments and we will correct it.", 32, "start", INK))
    return scene("What the data can and cannot say", "\n".join(b), "Data as of 2026-10-21 (BLS Q2 2026, ACS 2024). Spoken figures are rounded; exact figures are on screen.", 10)


SCENES = [("s01_hook", s01), ("s02_math", s02), ("s03_takehome", s03), ("s04_hud", s04), ("s05_spending", s05),
          ("s06_trend", s06), ("s07_scale", s07), ("s08_budgets", s08), ("s09_footnotes", s09), ("s10_close", s10)]

POSES = ["neutral", "brow", "paper", "point", "cross", "lens"]


def sprite(pose):
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;background:transparent}}svg{{display:block;font-family:{FONT}}}</style></head><body>
<svg width="600" height="800" viewBox="0 0 600 800" xmlns="http://www.w3.org/2000/svg"><defs><filter id="rough"><feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves="2" seed="3" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="3.5"/></filter></defs>
<g filter="url(#rough)">{stick(250, 130, 1.5, pose)}</g></svg></body></html>"""


def render(html_path, png_path, w, h, transparent=False):
    page = open(html_path, encoding="utf-8").read()
    if "@font-face" not in page:  # every page uses the licensed font file, never a system font
        open(html_path, "w", encoding="utf-8").write(page.replace("<style>", "<style>" + FONT_FACE, 1))
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--user-data-dir=/tmp/edge_headless_prof",
           f"--window-size={w},{h}", f"--screenshot={png_path}"]
    if transparent:
        cmd.append("--default-background-color=00000000")
    cmd.append("file://" + html_path)
    subprocess.run(cmd, capture_output=True, text=True)
    return os.path.exists(png_path)


def main():
    for d in ("html", "png", "sprites"):
        os.makedirs(os.path.join(HERE, d), exist_ok=True)
    ok = 0
    for name, fn in SCENES:
        hp = os.path.join(HERE, "html", name + ".html")
        open(hp, "w", encoding="utf-8").write(fn())
        if render(hp, os.path.join(HERE, "png", name + ".png"), W, Hh):
            ok += 1
    for p in POSES:
        hp = os.path.join(HERE, "html", "sprite_" + p + ".html")
        open(hp, "w", encoding="utf-8").write(sprite(p))
        render(hp, os.path.join(HERE, "sprites", p + ".png"), 600, 800, True)
    print("frames rendered:", ok, "of", len(SCENES))


if __name__ == "__main__":
    sys.exit(main())
