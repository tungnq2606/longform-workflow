#!/usr/bin/env python3
"""Gemini reviews generated images against the approved cast sheet or Shorts style references
(Antigravity CLI, Google plan quota).

Usage:
  agy_review.py VIDEO_DIR              review every scene frame that has no review for its current file
  agy_review.py VIDEO_DIR --only ID,ID review these items again
  agy_review.py VIDEO_DIR --all        review everything again
  agy_review.py VIDEO_DIR --workers 3  review several batches in parallel (default 3)

Writes images/runs/review.json: {id: {ok, score, problems[], fix, file, mtime, at}}. A review is advice:
the owner (dashboard) decides to keep, pick another variant or redo. Several images go into one call.
"""
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(os.path.dirname(HERE))
AGY = os.path.expanduser("~/.local/bin/agy")
MODEL = "gemini-4-argon-high"
BATCH = 4
SHORTS_BATCH = 1  # one image per Gemini call, reviewed in parallel: a 3-image batch took ~5 min, one image ~1.5 min

SCHEMA = {"type": "object", "properties": {"reviews": {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "string"}, "ok": {"type": "boolean"}, "score": {"type": "integer", "minimum": 1, "maximum": 5},
    "problems": {"type": "array", "items": {"type": "string"}},
    "fix": {"type": "string", "description": "one concise English sentence to append to the prompt when the image is redone; empty if ok"}},
    "required": ["id", "ok", "score", "problems", "fix"]}}}, "required": ["reviews"]}

RUBRIC = """Check each scene image against the cast sheet and its prompt. Report a problem only if you can see it:
1. Style: every person is a clothed stick figure with a round plain white head, dot eyes, a simple line mouth, thin black stick arms and white oval mitten hands. Problems: hair, nose, ears, fingers, skin colour, realistic or 3D look.
2. Identity: each named character matches the cast sheet (clothing, colours, accessories, one-sided items on the right side, relative height).
3. Scene: the action, pose, expression, setting and camera match the prompt.
4. No text: no letters, numbers, labels, logos or speech bubbles anywhere.
5. Quality: no merged or missing limbs, no headless figures, no extra characters, nothing cut off at the frame edge.
6. Era: for historical videos, nothing anachronistic.
Score 5 = ready to use, 4 = minor issue a viewer will not notice, 3 or less = should be redone. ok = score >= 4."""

SHORTS_RUBRIC = """Check each vertical 9:16 scene image against the approved channel style reference images (and any Parent locked-angle frame if listed) and its scene prompt.
IMPORTANT LANGUAGE RULE:
- Write `problems` in concise, natural VIETNAMESE (for the Vietnamese producer on the dashboard).
- Write `fix` in concise ENGLISH (one actionable sentence to append to the English image prompt if redone; empty string if ok).

Report a problem ONLY if you actually see it in the image:
1. Style Lock (vn-ligne-claire): 2D hand-drawn historical illustration with clean thin dark-brown/charcoal ink outlines, subtle organic hatching on wood/rock/reeds, flat two-tone muted earth-tone watercolor cel shading, and natural semi-realistic human proportions (~6 heads tall, warm tan skin). Score <= 3 if chibi/big round cartoon heads, stick figures, 3D CGI render, photorealistic photo, or neon oversaturated colors.
2. Locked-Angle Continuity (ONLY when a Parent frame is listed for edit_of): camera angle, horizon line, riverbanks, hills, and fixed structures must match the Parent frame closely — only the requested state/era change (e.g. rising tide submerging stakes, or modern river view) should differ.
3. Scene & 9:16 Framing: vertical 9:16 portrait composition, camera angle, action, props, counts (people, objects, lids, doors) and mood match the prompt and voiceover. Water must read clearly as rippled slate grey-blue water (NEVER a brown dirt road); people in water stand on boats/rafts or wade, never walk on top of the water surface.
4. Vietnamese Historical Accuracy: period-accurate tools, objects, buildings and attire exactly as the prompt describes them (shape, material, count, decoration). Fail on anachronisms (gunpowder weapons, European armor, modern machines or materials in older eras), invented foreign ornament (Aztec, Chinese, Indian motifs on Vietnamese objects), or wrong era attire.
5. No Text or UI: zero letters, numbers, captions, watermarks, banners, speech bubbles, or game UI anywhere in the image.
6. Quality & Anatomy: no merged/missing limbs, headless figures, garbled hands/tools, or main subject awkwardly cut off.
7. MUST NOT list: if the image shows anything the prompt's MUST NOT / Avoid list forbids (e.g. a second trapdoor), score at most 3, even when it looks minor.
Score 5 = ready to use, 4 = minor detail a mobile Shorts viewer will not notice, 3 or less = should be redone. ok = score >= 4."""


def strip_style_header(prompt_text):
    """Drop the repeated [STYLE LOCK] paragraph so the reviewer focuses on scene-specific requirements."""
    blocks = [b.strip() for b in prompt_text.strip().split("\n\n") if b.strip()]
    kept = [b for b in blocks if not b.startswith("[STYLE LOCK]")]
    return "\n\n".join(kept) if kept else prompt_text.strip()


def load_shorts_style_refs(style_name):
    sid = (style_name or "vn-ligne-claire").replace("-", "_")
    sp = os.path.join(WS, "tools", "imageprompts", "style", sid + ".json")
    if not os.path.exists(sp):
        return []
    obj = json.load(open(sp, encoding="utf-8"))
    out = []
    for r in obj.get("style_refs", [])[:3]:
        ap = os.path.abspath(os.path.join(WS, r))
        if os.path.exists(ap):
            out.append(ap)
    return out


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    vdir = os.path.abspath(a[0])
    img = os.path.join(vdir, "images")
    man_path = os.path.join(img, "prompts", "manifest.json")
    if not os.path.exists(man_path):
        sys.exit("Chưa có manifest.json (hãy bấm Tạo lại prompt trước): " + man_path)
    man_doc = json.load(open(man_path, encoding="utf-8"))
    man = man_doc.get("items", [])
    by_id = {it["id"]: it for it in man}
    shorts_mode = (man_doc.get("aspect") == "9:16") or (man_doc.get("style") == "vn-ligne-claire")

    runs_dir = os.path.join(img, "runs")
    os.makedirs(runs_dir, exist_ok=True)
    path = os.path.join(runs_dir, "review.json")
    reviews = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    only = set(a[a.index("--only") + 1].split(",")) if "--only" in a else None

    sheet = os.path.join(img, "refs", "cast_sheet.png")
    style_refs = []
    if shorts_mode:
        style_refs = load_shorts_style_refs(man_doc.get("style", "vn-ligne-claire"))
    else:
        if not os.path.exists(sheet):
            sys.exit("no approved cast sheet yet (images/refs/cast_sheet.png)")

    todo = []
    for it in man:
        f = os.path.join(img, it["save_as"])
        if it.get("kind") != "scene" or not os.path.exists(f):
            continue
        r = reviews.get(it["id"], {})
        if only and it["id"] not in only:
            continue
        if not only and "--all" not in a and abs(r.get("mtime", 0) - os.path.getmtime(f)) < 1:
            continue
        todo.append((it, f))

    if not todo:
        print("Không có ảnh mới cần kiểm (tất cả ảnh hiện có đã được kiểm)." if shorts_mode else "0 images to review (all current frames already reviewed).", flush=True)
        return

    bsize = SHORTS_BATCH if shorts_mode else BATCH
    workers = max(1, min(6, int(a[a.index("--workers") + 1]) if "--workers" in a else 3))
    batches = [todo[i:i + bsize] for i in range(0, len(todo), bsize)]
    print("%d images to review in %d batches, %d in parallel (%s)"
          % (len(todo), len(batches), workers, "9:16 Shorts style" if shorts_mode else "16:9 cast sheet"), flush=True)
    lock = threading.Lock()

    def review(batch):
        if shorts_mode:
            parts = []
            for idx, sr in enumerate(style_refs, 1):
                parts.append("Approved Channel Style Reference %d (art style reference ONLY — ink linework, proportions, muted watercolor palette): %s" % (idx, sr))
            for it, f in batch:
                raw_prompt = open(os.path.join(img, it["prompt_file"]), encoding="utf-8").read()
                scene_txt = strip_style_header(raw_prompt)
                lines = ["Scene image id %s: %s" % (it["id"], f)]
                if it.get("camera"):
                    lines.append("Camera: %s" % it["camera"])
                if it.get("vo"):
                    lines.append("Voiceover (VO): %s" % it["vo"])
                parent_id = it.get("edit_of")
                if parent_id and parent_id in by_id:
                    pf = os.path.join(img, by_id[parent_id]["save_as"])
                    if os.path.exists(pf):
                        lines.append("Parent locked-angle frame (edit_of=%s — camera angle, horizon & riverbanks MUST match this image): %s" % (parent_id, pf))
                lines.append("Prompt:\n%s" % scene_txt)
                parts.append("\n".join(lines))
            rubric = SHORTS_RUBRIC
            add_dir = WS
        else:
            parts = ["Image A (cast sheet, the reference): %s" % sheet]
            for it, f in batch:
                prompt = open(os.path.join(img, it["prompt_file"]), encoding="utf-8").read()
                scene = next((l for l in prompt.splitlines() if l.startswith("SCENE:")), "")
                chars = [l for l in prompt.splitlines() if l.startswith("- ")]
                parts.append("Scene image id %s: %s\n%s\n%s" % (it["id"], f, scene, "\n".join(chars)))
            rubric = RUBRIC
            add_dir = img

        task = ("You are an image reviewer. Open and look at every image file listed below (use your file viewing tool on each "
                "absolute path). Do not edit, generate or write anything.\n\n%s\n\n%s\n\nReturn one review per scene image id."
                % (rubric, "\n\n".join(parts)))
        t0 = time.time()
        p = subprocess.run([AGY, "-p", task, "--model", MODEL, "--output-format", "json", "--json-schema", json.dumps(SCHEMA),
                            "--print-timeout", "900s", "--dangerously-skip-permissions", "--add-dir", add_dir],
                           cwd=runs_dir, capture_output=True, text=True, timeout=1200)
        try:
            res = json.loads(p.stdout[p.stdout.find("{"):])
            body = res.get("structured_output") or res.get("response")
            data = body if isinstance(body, dict) else json.loads(body[body.find("{"):body.rfind("}") + 1])
        except (ValueError, AttributeError) as e:
            print("batch failed (%s): %s" % (e, (p.stderr or p.stdout)[-300:]), flush=True)
            return
        got = {r["id"]: r for r in data.get("reviews", [])}
        with lock:
            for it, f in batch:
                r = got.get(it["id"])
                if not r:
                    print("%-8s no review returned" % it["id"], flush=True)
                    continue
                r.update(file=os.path.relpath(f, img), mtime=os.path.getmtime(f), at=time.strftime("%Y-%m-%d %H:%M"))
                reviews[it["id"]] = r
                print("%-8s %s score %d %s" % (it["id"], "OK  " if r["ok"] else "REDO", r["score"], "; ".join(r["problems"])[:160]), flush=True)
            json.dump(reviews, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            print("batch of %d reviewed in %.0f s" % (len(batch), time.time() - t0), flush=True)

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(review, batches))


if __name__ == "__main__":
    main()
