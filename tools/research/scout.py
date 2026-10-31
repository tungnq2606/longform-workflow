#!/usr/bin/env python3
"""Topic scout: measures demand and competition on YouTube for a list of search phrases.

Usage:
  python3 tools/research/scout.py channels/<id>/research/scout/<name>.txt          (lines: "topic_id|search phrase")

For each phrase it reads the top 10 videos by view count and the top 10 by relevance, then the upload
date, views and channel subscribers of each (yt-dlp, no API key). Writes next to the input file:
  <name>.json   raw numbers (cache: delete it to refresh)
  <name>.csv    one row per phrase with the scores below, best first

Scores (all from real numbers, nothing estimated):
  demand      median views of the 10 most-viewed videos
  fresh_top   how many of those 10 were uploaded in the last 2 years (trend is live)
  fresh_rel   how many of the 10 relevance results are from the last year (others are making it now)
  small_wins  channels under 100k subscribers with a >=100k-view video in the last 2 years (room for new channels)
  score       log10(demand) + fresh_top/2 + small_wins - max(0, fresh_rel - 6)  (rough ranking only)
"""
import concurrent.futures as cf
import csv
import datetime as dt
import json
import math
import os
import statistics as st
import subprocess
import sys
import urllib.parse

if len(sys.argv) < 2:
    sys.exit(__doc__)
SRC = os.path.abspath(sys.argv[1])
BASE = os.path.splitext(SRC)[0]
TODAY = dt.date.today()
lines = [l.strip().split("|", 1) for l in open(SRC, encoding="utf-8") if "|" in l and not l.startswith("#")]


def flat(args):
    out = subprocess.run(["yt-dlp", "--flat-playlist", "-j", "--no-warnings"] + args, capture_output=True, text=True).stdout
    return [json.loads(x) for x in out.splitlines() if x.startswith("{")]


def meta(vid):
    out = subprocess.run(["yt-dlp", "--skip-download", "--no-warnings", "--print",
                          "%(upload_date)s\t%(view_count)s\t%(channel_follower_count)s\t%(channel)s\t%(duration)s\t%(title)s",
                          "https://www.youtube.com/watch?v=" + vid], capture_output=True, text=True).stdout.strip()
    f = out.split("\t")
    return vid, (dict(zip(["date", "views", "subs", "channel", "duration", "title"], f)) if len(f) == 6 else None)


if os.path.exists(BASE + ".json"):
    data = json.load(open(BASE + ".json"))
else:
    def search(item):
        tid, q = item
        top = flat(["--playlist-end", "10", "https://www.youtube.com/results?search_query=" + urllib.parse.quote(q) + "&sp=CAM%253D"])
        rel = flat(["ytsearch10:" + q])
        return {"id": tid, "q": q, "top": [v["id"] for v in top if v.get("id")], "rel": [v["id"] for v in rel if v.get("id")]}
    with cf.ThreadPoolExecutor(6) as ex:
        rows = list(ex.map(search, lines))
    ids = sorted({v for r in rows for v in r["top"] + r["rel"]})
    with cf.ThreadPoolExecutor(10) as ex:
        videos = {k: v for k, v in ex.map(meta, ids) if v}
    data = {"date": str(TODAY), "rows": rows, "videos": videos}
    json.dump(data, open(BASE + ".json", "w"), indent=1)


def num(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def age(d):
    try:
        return (TODAY - dt.date(int(d[:4]), int(d[4:6]), int(d[6:8]))).days
    except (TypeError, ValueError):
        return 99999


V = data["videos"]
out = []
for r in data["rows"]:
    top = [V[i] for i in r["top"] if i in V]
    rel = [V[i] for i in r["rel"] if i in V]
    demand = st.median([num(v["views"]) or 0 for v in top]) if top else 0
    fresh_top = sum(age(v["date"]) <= 730 for v in top)
    fresh_rel = sum(age(v["date"]) <= 365 for v in rel)
    small = {v["channel"] for v in top + rel
             if (num(v["subs"]) or 10 ** 9) < 100_000 and (num(v["views"]) or 0) >= 100_000 and age(v["date"]) <= 730}
    score = math.log10(demand + 1) + fresh_top / 2 + len(small) - max(0, fresh_rel - 6)
    best = max(top, key=lambda v: num(v["views"]) or 0) if top else {}
    out.append({"topic": r["id"], "query": r["q"], "score": round(score, 2), "demand": int(demand), "fresh_top": fresh_top,
                "fresh_rel": fresh_rel, "small_wins": len(small), "small_channels": "; ".join(sorted(small)),
                "top_video": f'{best.get("title", "")} ({best.get("channel", "")}, {num(best.get("views")) or 0:,} views, {best.get("date", "")})'})
out.sort(key=lambda x: -x["score"])
with open(BASE + ".csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0]))
    w.writeheader()
    w.writerows(out)
print(f"data from {data['date']}; wrote {BASE}.csv")
for o in out:
    print(f"{o['score']:>6} {o['demand']:>11,} top2y {o['fresh_top']:>2}/10 rel1y {o['fresh_rel']:>2}/10 small {o['small_wins']}  {o['query']}")
