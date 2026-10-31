#!/usr/bin/env python3
"""Gemini checks image prompts BEFORE they are generated (text only, cheap) and adds the missing constraints.

For every scene image still to be made (agy state "pending"), Gemini reads the full prompt, the shot notes
(camera, voice-over, characters) and the channel's prompt lessons, and lists short constraints that close the
gaps that would otherwise fail review: people count, anatomy, period accuracy (ships, clothes, architecture),
physics of the action, text on objects, what a reference image may and may not lend. The prompt files are
not changed: images/runs/preflight.json stores the fixes per prompt hash and agy_images.py appends them.

Usage: preflight.py VIDEO_DIR [--only ID,ID] [--all]
"""
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lessons  # noqa: E402

BATCH = 8
SCHEMA = {"type": "object", "properties": {"checks": {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "string"}, "risk": {"type": "string", "enum": ["low", "medium", "high"]},
    "fixes": {"type": "array", "items": {"type": "string"}}, "why": {"type": "string"}},
    "required": ["id", "risk", "fixes", "why"]}}}, "required": ["checks"]}

TASK = """You are the pre-flight checker of an AI image pipeline (Nano Banana image model, 2D illustrated style).
Before each image is generated, predict what a strict reviewer would reject and add constraints that prevent it.
For each item below return:
- "fixes": 0-5 short English imperative sentences to append to the prompt. Only add what the prompt is missing
  or leaves ambiguous; do not restate the style block; never contradict the prompt. Typical gaps: exact number of
  people and that nobody else appears; hands/limbs/faces; period accuracy (ships, clothing, weapons, buildings of
  the stated era and country, e.g. 10th-century Southern Han war junks with batten sails, not Viking ships);
  physical logic of the action (what pierces what, water levels, directions); no letters or characters on flags,
  signs or objects; when a style reference image is attached, copy only its drawing style, not its landscape,
  buildings or people.
- "risk": how likely the image fails review as written (low, medium, high). "why": one short sentence.
Respect the channel lessons below: if a lesson already covers a gap it will be appended anyway, do not repeat it.

CHANNEL LESSONS:
{lessons}

ITEMS:
{items}"""


def load_json(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def prompt_hash(text):
    return hashlib.sha1(text.strip().encode()).hexdigest()[:16]


def fixes_for(vdir, iid, prompt):
    """Fixes stored for this exact prompt text (a changed prompt needs a new check)."""
    p = load_json(os.path.join(vdir, "images", "runs", "preflight.json"), {}).get(iid)
    return p["fixes"] if p and p.get("hash") == prompt_hash(prompt) else []


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    vdir = os.path.abspath(a[0])
    img = os.path.join(vdir, "images")
    only = set(a[a.index("--only") + 1].split(",")) if "--only" in a else None
    man = load_json(os.path.join(img, "prompts", "manifest.json"), {"items": []})
    state = load_json(os.path.join(img, "runs", "state.json"), {})
    shots = {s["id"]: s for s in load_json(os.path.join(img, "shots.json"), {}).get("shots", [])}
    out_p = os.path.join(img, "runs", "preflight.json")
    done = load_json(out_p, {})
    todo = []
    for it in man["items"]:
        if it["kind"] != "scene" or (only and it["id"] not in only):
            continue
        if not only and "--all" not in a and state.get(it["id"], {}).get("status", "pending") != "pending":
            continue
        prompt = open(os.path.join(img, it["prompt_file"]), encoding="utf-8").read()
        if done.get(it["id"], {}).get("hash") == prompt_hash(prompt):
            continue  # this exact prompt was checked already
        sh = shots.get(it["id"], {})
        todo.append({"id": it["id"], "hash": prompt_hash(prompt), "prompt": prompt,
                     "notes": {k: sh.get(k) for k in ("camera", "vo", "characters", "background_people", "location")
                               if sh.get(k)}, "refs": it.get("refs", [])})
    if not todo:
        print("preflight: nothing new to check", flush=True)
        return 0
    les = [l for l in lessons.load(vdir) if l.get("target", "image") == "image"]
    print("preflight: Gemini checks %d prompt(s) before generation" % len(todo), flush=True)
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        task = TASK.replace("{lessons}", json.dumps([l["rule"] for l in les], ensure_ascii=False, indent=1)).replace(
            "{items}", json.dumps([{k: b[k] for k in ("id", "prompt", "notes", "refs")} for b in batch], ensure_ascii=False, indent=1))
        try:
            data = lessons.run_agy_json(task, SCHEMA, os.path.join(img, "runs", "agy_workspace"))
        except Exception as e:  # noqa: BLE001  a failed check never blocks generation
            print("preflight: Gemini call failed (%s); generating without extra fixes" % e, flush=True)
            continue
        got = {c["id"]: c for c in data.get("checks", [])}
        done = load_json(out_p, {})
        for b in batch:
            c = got.get(b["id"])
            if not c:
                continue
            done[b["id"]] = {"hash": b["hash"], "fixes": c["fixes"][:5], "risk": c["risk"], "why": c["why"],
                             "at": time.strftime("%Y-%m-%d %H:%M")}
            print("%-8s risk %-6s +%d fix(es)  %s" % (b["id"], c["risk"], len(c["fixes"]), c["why"][:110]), flush=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(done, f, indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
