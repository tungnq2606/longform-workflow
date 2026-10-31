#!/usr/bin/env python3
"""Thumbnail candidates made by Gemini (Antigravity CLI) in the locked character style.

Usage: agy_thumb.py VIDEO_DIR "concept" ["BIG TEXT"] [--prompt-only]
  concept        what the thumbnail shows, e.g. "WORKER looks shocked at a giant rent bill bigger than him"
  BIG TEXT       optional, at most 4 words, drawn large on the image
  --model ID     agy model (default: agy_images.MODEL)
  --prompt-only  build the same prompt but do not call Gemini: save it as upload/thumbs/prompt_NN.txt
                 for the manual Google Flow route (attach the figures crop it names)

Uses the approved cast sheet (images/refs/cast_sheet.png) as the character reference when it exists.
Every variant Gemini makes is saved as upload/thumbs/thumb_NN.png at 1280x720; pick one in the dashboard.
"""
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "imageprompts"))
import agy_images as ai  # noqa: E402
import make_prompts as mp  # noqa: E402


def main():
    prompt_only = "--prompt-only" in sys.argv
    argv = [a for a in sys.argv[1:] if a != "--prompt-only"]
    model = ai.MODEL
    if "--model" in argv:  # e.g. another account without the default model
        i = argv.index("--model")
        model = argv[i + 1]
        del argv[i:i + 2]
    args = argv
    if len(args) < 2:
        sys.exit(__doc__)
    v = os.path.abspath(args[0])
    concept = args[1]
    text = args[2].strip() if len(args) > 2 else ""
    if len(text.split()) > 4:
        sys.exit("thumbnail text: at most 4 words")
    cast = json.load(open(os.path.join(v, "images", "cast.json"), encoding="utf-8")) if os.path.exists(os.path.join(v, "images", "cast.json")) else {"characters": []}
    st = mp.load_style(cast.get("style", "stickman-v1"))  # the channel's look (fossil-receipts: stickman-v2)
    sheet = os.path.join(v, "images", "refs", "cast_sheet.png")
    refs = []
    if os.path.exists(sheet):  # figures only: the expression-head row at the bottom gets copied into thumbnails otherwise
        crop = os.path.join(v, "images", "refs", "cast_sheet_figures.png")
        if not os.path.exists(crop) or os.path.getmtime(crop) < os.path.getmtime(sheet):  # a composed sheet ships its own
            ai.run([os.path.join(HERE, "croptop"), sheet, crop, "0.79"])
        refs = [crop]
    named = [c for c in cast["characters"] if re.search(r"\b%s\b" % c["name"], concept)]
    lines = []
    if refs:
        lines.append("REFERENCES: Image 1 is the approved cast sheet, used ONLY to know what the named characters look like (head, face, clothing, colours, accessories). "
                     "Draw a brand-new illustration: do not show the sheet itself, its rows, labels, expression circles, white background or any character that is not named below.")
    lines += ["", st["style"], "", "YOUTUBE THUMBNAIL: " + concept]
    for c in named:
        lines.append('%s ("%s" on the cast sheet): %s' % (c["name"], c["name"], c["card"]))
    lines += ["COMPOSITION: one bold, simple idea readable at a small size: one or two large characters with big clear expressions, "
              "one oversized key object, strong contrast between subject and background, uncluttered background, nothing important near the bottom-right corner (the video length badge sits there)."]
    if text:  # the words are drawn by code afterwards (image models misspell and repeat words)
        lines.append("Leave the upper-right third of the image calm and empty (plain sky or wall) for a big title added later.")
    lines.append(st["exclusion_scene"])
    lines.append("FORMAT: one single widescreen 16:9 landscape image.")
    prompt = "\n".join(lines)
    out = os.path.join(v, "upload", "thumbs")
    os.makedirs(out, exist_ok=True)
    if prompt_only:  # manual route (Google Flow): same prompt, no generation
        n = max([int(m.group(1)) for m in (re.match(r"prompt_(\d+)\.txt$", f) for f in os.listdir(out)) if m] or [0]) + 1
        dst = os.path.join(out, "prompt_%02d.txt" % n)
        open(dst, "w", encoding="utf-8").write(prompt + "\n")
        print("prompt:", os.path.relpath(dst, v))
        print("attach:", ", ".join(os.path.relpath(r, v) for r in refs) or "none")
        if text:
            print("title to draw afterwards:", text.upper())
        return
    name = "thumb_%d" % int(time.time())
    path_line = ("- ImagePaths: [%s] (in this order)\n" % ", ".join('"%s"' % p for p in refs)) if refs else ""
    task = ai.PREAMBLE.format(name=name, paths=path_line, prompt=prompt)
    t0 = time.time()
    work = os.path.join(v, "images", "runs", "agy_workspace")
    os.makedirs(work, exist_ok=True)
    p = ai.run([ai.AGY, "-p", task, "--model", model, "--output-format", "json", "--print-timeout", "600s"], cwd=work, timeout=900)
    try:
        conv = json.loads(p.stdout[p.stdout.find("{"):]).get("conversation_id", "")
    except ValueError:
        conv = ""
    files = ai.find_outputs(conv, name, t0) if conv else []
    if not files:
        sys.exit("no image produced: " + (p.stderr or p.stdout)[-400:])
    n = max([int(m.group(1)) for m in (re.match(r"thumb_(\d+)\.png$", f) for f in os.listdir(out)) if m] or [0])
    for src in files:
        n += 1
        dst = os.path.join(out, "thumb_%02d.png" % n)
        ai.run(["sips", "-s", "format", "png", src, "--out", dst])
        w, h = ai.dims(dst)
        s = max(1280 / w, 720 / h)
        ai.run(["sips", "-z", str(round(h * s)), str(round(w * s)), dst])
        ai.run(["sips", "-c", "720", "1280", dst])
        open(dst + ".txt", "w").write(prompt + "\n")
        if text:
            add_title(dst, text)
        print("thumbnail candidate:", os.path.relpath(dst, v))


def add_title(png, text):
    """Draw the title in the channel font with a thick outline, top right, through headless Edge (same renderer as the kit)."""
    sys.path.insert(0, os.path.join(HERE, "..", "kit"))
    import build_visuals as bv
    html = png[:-4] + "_title.html"
    words = text.upper().split()
    lines = [" ".join(words[:2]), " ".join(words[2:])] if len(words) > 2 else [" ".join(words)]
    size = 150 if max(len(l) for l in lines) <= 9 else 118
    open(html, "w").write("""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;width:1280px;height:720px;overflow:hidden}
body{background:url('file://%s') center/cover no-repeat}
div{position:absolute;right:40px;top:30px;width:640px;text-align:center;font-family:'PatrickHand',sans-serif;font-weight:bold;
font-size:%dpx;line-height:1.0;color:#fff;-webkit-text-stroke:14px #111;paint-order:stroke fill;letter-spacing:2px}
</style></head><body><div>%s</div></body></html>""" % (png, size, "<br>".join(lines)))
    bv.render(html, png, 1280, 720)
    os.remove(html)


if __name__ == "__main__":
    main()
