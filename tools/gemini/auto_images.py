#!/usr/bin/env python3
"""Generate a video's scene images, have Gemini review them, and redo the bad ones by itself.

Decision per scene image (owner rule, 2026-10-28), from the Gemini review score of the current file:
  4-5    passes (owner, 2026-10-29: 4 is good enough)
  3      waits for the owner: dashboard "Cần bạn duyệt" (approve keeps it, redo makes it again)
  1-2    redone automatically with the review's fix, at most --max-redo times; after that it waits for the owner
An owner approval is stored in images/runs/approvals.json for that exact file (a new file needs a new approval).

Usage:
  auto_images.py VIDEO_DIR [--workers 4] [--max-redo 2]
  auto_images.py VIDEO_DIR --only S04A,S07B   queue these for an owner's redo (made again, reviewed, rule applied)
One runner per video: requests that arrive while it runs go to images/runs/image_queue.json and are taken
before it ends. The owner's pause (images/runs/auto.json) stops it between rounds.

Runs tools/gemini/agy_images.py and agy_review.py; counts redos in images/runs/auto_state.json.
"""
import argparse
import json
import os
import subprocess
import sys
import time

WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PY = sys.executable
PASS = 4  # lowest review score accepted without the owner (2026-10-29; was 5)
sys.path.insert(0, os.path.join(WS, "tools"))
import notify  # noqa: E402  Telegram, no-op when not configured
import flowcli  # noqa: E402
import workqueue  # noqa: E402  owner requests queued on disk
sys.path.insert(0, os.path.join(WS, "tools", "gemini"))
import lessons  # noqa: E402  channel prompt lessons


def load_json(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def verdict(score, approved):
    """'pass', 'ask' or 'redo' for one reviewed image."""
    if approved or score >= PASS:
        return "pass"
    return "ask" if score >= 3 else "redo"


def approved_now(vdir, sid, path):
    a = load_json(os.path.join(vdir, "images", "runs", "approvals.json"), {}).get("images", {}).get(sid)
    return bool(a and os.path.exists(path) and abs(a.get("mtime", 0) - os.path.getmtime(path)) < 1)


def tool(*args):
    return subprocess.run([PY, "-u"] + list(args), cwd=WS).returncode


def run_pass(vdir, args, state, only):
    """One generate -> review -> auto-redo cycle, for every scene (only=None) or for the given ids."""
    img = os.path.join(vdir, "images")
    state_p = os.path.join(img, "runs", "auto_state.json")
    scenes = [i for i in load_json(os.path.join(img, "prompts", "manifest.json"), {"items": []})["items"] if i["kind"] == "scene"]
    if only:
        scenes = [i for i in scenes if i["id"] in only]  # judge only what the owner asked for
        for sid in only:
            tool("tools/gemini/agy_images.py", vdir, "--redo", sid)
            state[sid] = {"redos": 0}
    summary = {"pass": [], "ask": [], "redo": [], "unreviewed": []}
    for rnd in range(1, args.max_redo + 2):
        if workqueue.pause_requested(vdir):
            print("paused by the owner: stopping before round %d" % rnd, flush=True)
            break
        tool("tools/gemini/preflight.py", vdir, *(["--only", ",".join(only)] if only else []))
        print("== round %d: generate %s" % (rnd, ",".join(only) if only else "all pending"), flush=True)
        tool("tools/gemini/agy_images.py", vdir, "--workers", str(args.workers), *(["--only", ",".join(only)] if only else []))
        print("== round %d: Gemini review" % rnd, flush=True)
        tool("tools/gemini/agy_review.py", vdir, "--workers", "5", *(["--only", ",".join(only)] if only else []))

        rv = load_json(os.path.join(img, "runs", "review.json"), {})
        redo, summary = [], {"pass": [], "ask": [], "redo": [], "unreviewed": []}
        for it in scenes:
            sid, path = it["id"], os.path.join(img, it["save_as"])
            if not os.path.exists(path):
                continue
            r = rv.get(sid)
            if not r or abs(r.get("mtime", 0) - os.path.getmtime(path)) >= 1:
                summary["unreviewed"].append(sid)
                continue
            v = verdict(r.get("score", 0), approved_now(vdir, sid, path))
            st = state.setdefault(sid, {"redos": 0})
            if v == "redo" and ((it.get("route") == "manual" and not flowcli.available()) or st["redos"] >= args.max_redo):
                v = "ask"  # hand-made image (no gflow), or out of automatic tries: the owner decides
            st.update(verdict=v, score=r.get("score"), problems=r.get("problems", []), at=time.strftime("%Y-%m-%d %H:%M"))
            summary[v].append(sid)
            if v == "redo":
                st["redos"] += 1
                redo.append(sid)
        with open(state_p, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=1, ensure_ascii=False)
        if not redo:
            break
        print("redo automatically (score 1-2): %s" % ", ".join(redo), flush=True)
        for sid in redo:
            tool("tools/gemini/agy_images.py", vdir, "--redo", sid)
        only = redo
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-redo", type=int, default=2)
    ap.add_argument("--only", help="comma-separated ids to redo now; they get a fresh set of automatic redos")
    args = ap.parse_args()
    vdir = os.path.abspath(args.video)
    lock = workqueue.hold(vdir, "auto_images.lock")
    if args.only:
        workqueue.add_images(vdir, [i for i in args.only.split(",") if i])
    if not lock:  # one image runner per video; the running one takes the queue before it ends
        print("An image run for this video is already going; the request is queued and it will take it.", flush=True)
        return 0
    state = load_json(os.path.join(vdir, "images", "runs", "auto_state.json"), {})
    full = not args.only
    while not workqueue.pause_requested(vdir):
        queued = workqueue.take_images(vdir)
        if not queued and not full:
            break
        before = made_counts(vdir)
        summary = run_pass(vdir, args, state, queued or None)
        full = False if not queued else full
        after = made_counts(vdir)
        report(vdir, state, summary, [k for k in after if after[k] != before.get(k, 0)])
        lessons.learn_in_background(vdir)  # what the reviews rejected becomes a rule for later prompts (minutes; never blocks)
    if workqueue.pause_requested(vdir):
        print("paused by the owner; queued images wait for Tiếp tục", flush=True)
    return 0


def made_counts(vdir):
    st = load_json(os.path.join(vdir, "images", "runs", "state.json"), {})
    return {k: len(v.get("variants", [])) for k, v in st.items()}


def report(vdir, state, summary, changed=None):
    print("\nPASS (5/5): %d   NEED YOUR DECISION: %d   not reviewed: %d" % (
        len(summary["pass"]), len(summary["ask"]), len(summary["unreviewed"])), flush=True)
    for sid in summary["ask"]:
        st = state[sid]
        print("  ask %-6s %s/5  %s" % (sid, st.get("score"), "; ".join(st.get("problems", []))[:160]), flush=True)
    if not changed and not summary["ask"]:
        return  # nothing was made in this pass and nothing waits: no message
    rv = load_json(os.path.join(vdir, "images", "runs", "review.json"), {})
    msg = "%s · lượt ảnh vừa làm: %s" % (os.path.basename(vdir), ", ".join(
        "%s (%s/5)" % (k, rv.get(k, {}).get("score", "?")) for k in sorted(changed or [])) or "không tạo ảnh mới")
    if summary["ask"]:
        msg += "\nCần bạn duyệt %d ảnh: %s" % (len(summary["ask"]), ", ".join(
            "%s (%s/5)" % (sid, state[sid].get("score")) for sid in summary["ask"]))
    if summary["unreviewed"]:
        msg += "\nChưa kiểm được: %s" % ", ".join(summary["unreviewed"])
    notify.send(msg + "\n" + notify.video_link(vdir))


if __name__ == "__main__":
    sys.exit(main())
