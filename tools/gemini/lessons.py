#!/usr/bin/env python3
"""Prompt lessons per channel: what Gemini's reviews keep rejecting becomes a fixed rule in later prompts.

channels/<id>/prompt_lessons.json = {"lessons": [{"id", "target": "image"|"clip", "when": [keywords],
"rule": "...", "count": n, "examples": ["video/shot", ...], "added": "YYYY-MM-DD"}]}
- learn(VIDEO): Gemini reads the new review problems (images/runs/review.json, clip_review.json; only scores
  below 5 not seen before) and merges them into the channel's lessons: general rules only, never shot-specific.
- rules_for(...): the rules whose keywords appear in a prompt (or with no keywords), most frequent first;
  agy_images.py / flow_clips.py append them to every prompt they send.

Usage:
  lessons.py learn VIDEO_DIR         update the channel's lessons from this video's reviews
Runners call learn_in_background(): the Gemini merge takes minutes and must never hold up a run or a pause.
  lessons.py show VIDEO_DIR|CHANNEL  print the lessons
"""
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time

WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AGY = os.path.expanduser("~/.local/bin/agy")
MODEL = "gemini-4-argon-high"
MAX_RULES = 8  # per prompt: enough to steer, short enough not to drown the scene description

SCHEMA = {"type": "object", "properties": {"lessons": {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "string"}, "target": {"type": "string", "enum": ["image", "clip"]},
    "when": {"type": "array", "items": {"type": "string"}}, "rule": {"type": "string"},
    "count": {"type": "integer"}, "examples": {"type": "array", "items": {"type": "string"}}},
    "required": ["id", "target", "when", "rule", "count", "examples"]}}}, "required": ["lessons"]}

TASK = """You maintain the prompt lessons of one YouTube channel's AI image and video pipeline.
Each lesson is a short, general rule that is appended to future generation prompts so the same mistake is not
made again. Below are the CURRENT lessons (JSON) and NEW review problems (Gemini rejected these images/clips).

Return the full updated lesson list:
- Merge each new problem into an existing lesson when it is the same kind of mistake (raise "count", add the
  example "video/shot"), otherwise add a new lesson. Keep every existing lesson unless a new one replaces it.
- "rule": one English imperative sentence the image/video model can follow, positive and concrete
  (e.g. "Show exactly the people listed in the prompt and no one else."). Never mention a specific shot id.
- "when": 1-6 lowercase keywords that appear in prompts where the rule matters (e.g. ["flag", "banner"]);
  use [] only for rules that apply to every prompt of that target.
- "target": "image" for still images, "clip" for Veo motion.
- Skip problems that are one-off taste notes, not a repeatable mistake. At most 40 lessons in total.

CURRENT LESSONS:
{current}

NEW PROBLEMS:
{problems}"""


def load_json(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def channel_dir(path):
    """channels/<id> for a video folder or a channel folder."""
    parts = os.path.relpath(os.path.abspath(path), os.path.join(WS, "channels")).split(os.sep)
    return os.path.join(WS, "channels", parts[0])


def lessons_path(path):
    return os.path.join(channel_dir(path), "prompt_lessons.json")


def load(path):
    return load_json(lessons_path(path), {"lessons": []})["lessons"]


def rules_for(path, text, target="image"):
    """Rules to append to a prompt: lessons of this target whose keywords occur in the text."""
    low = text.lower()
    hits = [l for l in load(path) if l.get("target", "image") == target
            and (not l.get("when") or any(k.lower() in low for k in l["when"]))]
    hits.sort(key=lambda l: -l.get("count", 1))
    return [l["rule"] for l in hits[:MAX_RULES]]


def with_rules(path, prompt, target="image", extra=()):
    """The prompt plus a MUST block (lessons and preflight fixes); unchanged when there is nothing to add."""
    rules = list(dict.fromkeys(list(extra) + rules_for(path, prompt, target)))
    if not rules:
        return prompt
    return prompt.rstrip() + "\n\nMUST (lessons from earlier reviews of this channel):\n" + "\n".join("- " + r for r in rules)


def run_agy_json(task, schema, work_dir):
    os.makedirs(work_dir, exist_ok=True)
    p = subprocess.run([AGY, "-p", task, "--model", MODEL, "--output-format", "json", "--json-schema", json.dumps(schema),
                        "--print-timeout", "900s", "--dangerously-skip-permissions"],
                       cwd=work_dir, capture_output=True, text=True, timeout=1200)
    res = json.loads(p.stdout[p.stdout.find("{"):])
    body = res.get("structured_output") or res.get("response")
    return body if isinstance(body, dict) else json.loads(body[body.find("{"):body.rfind("}") + 1])


def new_problems(vdir):
    """Review problems (score < 5) of this video not yet turned into lessons; marks them as seen."""
    runs = os.path.join(vdir, "images", "runs")
    seen_p = os.path.join(runs, "lessons_seen.json")
    seen = set(load_json(seen_p, []))
    name = os.path.basename(vdir)
    out = []
    for fname, target in (("review.json", "image"), ("clip_review.json", "clip")):
        for sid, r in load_json(os.path.join(runs, fname), {}).items():
            if r.get("score", 5) >= 5 or not r.get("problems"):
                continue
            key = hashlib.sha1(("%s|%s|%s" % (target, sid, r["problems"])).encode()).hexdigest()[:16]
            if key in seen:
                continue
            seen.add(key)
            out.append({"target": target, "example": "%s/%s" % (name, sid), "score": r.get("score"),
                        "problems": r["problems"], "fix": r.get("fix", "")})
    return out, seen, seen_p


def learn_in_background(vdir):
    """Start `lessons.py learn VIDEO` detached and return at once (its output goes to images/runs/lessons.log)."""
    vdir = os.path.abspath(vdir)
    log = open(os.path.join(vdir, "images", "runs", "lessons.log"), "a")
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "learn", vdir], stdout=log, stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL, start_new_session=True, cwd=WS)
    print("lessons: learning in the background (images/runs/lessons.log)", flush=True)


def learn(vdir):
    vdir = os.path.abspath(vdir)
    # one merge per channel at a time: two runs ending together would overwrite each other's lessons
    lk = open(lessons_path(vdir) + ".lock", "w")
    try:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("lessons: another merge for this channel is running; these problems wait for the next one", flush=True)
        return 0
    probs, seen, seen_p = new_problems(vdir)
    if not probs:
        print("lessons: no new review problems", flush=True)
        return 0
    current = load(vdir)
    task = TASK.replace("{current}", json.dumps(current, ensure_ascii=False, indent=1)).replace(
        "{problems}", json.dumps(probs, ensure_ascii=False, indent=1))
    try:
        data = run_agy_json(task, SCHEMA, os.path.join(WS, "dashboard", "agy_work"))
    except Exception as e:  # noqa: BLE001  lessons are an improvement, never a reason to fail a run
        print("lessons: Gemini call failed (%s); will retry next time" % e, flush=True)
        return 1
    today = time.strftime("%Y-%m-%d")
    old = {l["id"]: l for l in current}
    merged = []
    for l in data.get("lessons", [])[:40]:
        l["added"] = old.get(l["id"], {}).get("added", today)
        merged.append(l)
    tmp = lessons_path(vdir) + ".tmp"  # runners read this file while the merge runs: replace it in one step
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"updated": today, "lessons": merged}, f, indent=1, ensure_ascii=False)
    os.replace(tmp, lessons_path(vdir))
    with open(seen_p, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f)
    print("lessons: %d problems -> %d lessons (%d new)" % (len(probs), len(merged), len(set(l["id"] for l in merged) - set(old))), flush=True)
    return 0


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("learn", "show"):
        sys.exit(__doc__)
    if sys.argv[1] == "learn":
        return learn(sys.argv[2])
    for l in load(sys.argv[2]):
        print("[%s x%d] %s  (when: %s)" % (l.get("target"), l.get("count", 1), l["rule"], ", ".join(l.get("when", [])) or "always"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
