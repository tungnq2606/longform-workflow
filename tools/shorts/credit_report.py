#!/usr/bin/env python3
"""Veo credits per video of one channel, to show whether each new Short costs less than the last.

  credit_report.py CHANNEL_DIR        e.g. channels/vn-history

Reads every VIDEO/images/runs/flow_clips.jsonl. A clip counts as billed when Flow returned its media id (also a
paid clip fetched later); an exit 9 after submit that was never recovered may or may not have been billed and is
shown apart. Since 2026-10-30 flow_clips.py logs the Flow balance before and after each clip ("credits_spent"):
those measured numbers are used when present, otherwise the clip count times the rough price below.
"""
import json
import os
import sys

PRICE = {"lite": 12, "fast": 20}  # rough credits per clip (gflow author's lite measurement, Flow's Fast price)


def video_report(vdir):
    logf = os.path.join(vdir, "images", "runs", "flow_clips.jsonl")
    if not os.path.exists(logf):
        return None
    media = {"lite": set(), "fast": set()}
    pending = {}  # (shot, stage) -> submits gflow lost (exit 7/9 without a media id), until a later fetch finds one
    measured, measured_n = 0, 0
    for line in open(logf, encoding="utf-8"):
        r = json.loads(line)
        stage, key = r.get("stage"), (r.get("id"), r.get("stage"))
        if stage not in media:
            continue  # 1080p upscale exports cost nothing
        res = r.get("result") if isinstance(r.get("result"), dict) else {}
        if res.get("media_id"):
            media[stage].add(res["media_id"])
            if res.get("recovered") and pending.get(key):
                pending[key] -= 1
        elif r.get("code") in (7, 9):
            pending[key] = pending.get(key, 0) + 1
        if isinstance(r.get("credits_spent"), int):
            measured += r["credits_spent"]
            measured_n += 1
    lost = {s: sum(n for (_, st), n in pending.items() if st == s) for s in media}
    shots = json.load(open(os.path.join(vdir, "images", "shots.json"), encoding="utf-8")).get("shots", [])
    est = sum(len(media[s]) * PRICE[s] for s in media)
    return {"video": os.path.basename(vdir), "shots": len(shots),
            "active": sum(1 for s in shots if s.get("motion_mode") == "active"),
            "lite": len(media["lite"]), "fast": len(media["fast"]), "lost": lost["lite"] + lost["fast"],
            "estimate": est, "estimate_max": est + sum(lost[s] * PRICE[s] for s in media),
            "measured": measured if measured_n else None, "measured_clips": measured_n}


def main():
    cdir = sys.argv[1]
    rows = [r for r in (video_report(os.path.join(cdir, d)) for d in sorted(os.listdir(cdir))
                        if os.path.isdir(os.path.join(cdir, d))) if r]
    print("| Video | Shots (active) | veo-lite | veo-fast | lost by gflow (maybe billed) | Clips per shot | Credits | Credits per shot | vs previous |")
    print("|---|---|---|---|---|---|---|---|---|")
    prev = None
    for r in rows:
        credits = r["measured"] if r["measured"] is not None else r["estimate"]
        label = "%d measured" % credits if r["measured"] is not None else "~%d (max ~%d)" % (credits, r["estimate_max"])
        per_shot = credits / max(1, r["shots"])
        change = "" if prev is None else "%+.0f%%" % (100.0 * (per_shot - prev) / prev)
        print("| %s | %d (%d) | %d | %d | %d | %.2f | %s | %.1f | %s |" % (
            r["video"], r["shots"], r["active"], r["lite"], r["fast"], r["lost"],
            (r["lite"] + r["fast"]) / max(1, r["shots"]), label, per_shot, change))
        prev = per_shot
    return 0


if __name__ == "__main__":
    sys.exit(main())
