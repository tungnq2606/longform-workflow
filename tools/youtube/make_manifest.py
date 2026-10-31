#!/usr/bin/env python3
"""Build upload/manifest.json for one video from its upload/upload.txt.

Usage:
  python3 tools/youtube/make_manifest.py VIDEO --at "2026-10-30 09:00" [--tz America/New_York]
  python3 tools/youtube/make_manifest.py VIDEO            (no schedule: private upload)

The manifest is read by youtube_upload.py, which only does a dry run unless
it gets --execute (and --confirm-public for a scheduled upload).
Channel rules baked in: not made for kids, altered/synthetic content = yes
(AI voice), category Education, no subscriber notification.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

EDUCATION = "27"


def sections(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    name = None
    for line in text.splitlines(keepends=True):
        m = re.match(r"=== (.+?) ===\s*$", line)
        if m:
            name = m.group(1).split(" (")[0].strip().upper()
            out[name] = ""
        elif name:
            out[name] += line
    return out


def description(block: str) -> str:
    parts = re.split(r"^-{10,}\s*$", block, flags=re.M)
    if len(parts) < 3:
        sys.exit("upload.txt: DESCRIPTION must sit between two lines of dashes")
    return parts[1].strip("\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", help="channels/<id>/videos/NNN-slug")
    ap.add_argument("--at", help='publish time, "YYYY-MM-DD HH:MM" in --tz')
    ap.add_argument("--tz", default="America/New_York", help="time zone for --at (default America/New_York)")
    ap.add_argument("--playlist", help="playlist ID to add the video to")
    args = ap.parse_args()

    video = Path(args.video).expanduser().resolve()
    status_md = video / "VIDEO.md"
    if status_md.is_file() and re.search(r"^Status:\s*published", status_md.read_text(), re.M):
        sys.exit(f"{video.name} is published and closed; refusing to build an upload for it")

    upload_txt = video / "upload" / "upload.txt"
    if not upload_txt.is_file():
        sys.exit(f"missing {upload_txt}")
    sec = sections(upload_txt.read_text(encoding="utf-8"))

    title = sec.get("TITLE", "").strip()
    if not title:
        sys.exit("upload.txt: TITLE is empty")
    desc = description(sec.get("DESCRIPTION", ""))
    tags = [t.strip() for t in sec.get("TAGS", "").replace("\n", ",").split(",") if t.strip()]

    mp4s = sorted((video / "render").glob("*_1440p.mp4"))
    if len(mp4s) != 1:
        sys.exit(f"need exactly one render/*_1440p.mp4, found {len(mp4s)}")
    thumb = video / "upload" / "thumbnail.png"
    if not thumb.is_file():
        thumb = video / "upload" / "thumbnail.jpg"
    warnings = []
    if not thumb.is_file():
        warnings.append("no upload/thumbnail.png or .jpg: video goes up without a custom thumbnail")

    publish_at = None
    if args.at:
        local = datetime.strptime(args.at, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(args.tz))
        publish_at = local.isoformat()

    manifest = {
        "video_path": "../render/" + mp4s[0].name,
        "snippet": {"title": title, "description": desc, "tags": tags, "category_id": EDUCATION},
        "status": {
            "privacy_status": "private",
            "publish_at": publish_at,
            "made_for_kids": False,
            "contains_synthetic_media": True,
            "notify_subscribers": False,
        },
        "assets": {
            "thumbnail_path": thumb.name if thumb.is_file() else None,
            "playlist_id": args.playlist,
        },
        "execution": {"result_log_dir": "."},
    }
    out = video / "upload" / "manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    for w in warnings:
        print(f"warning: {w}")
    if publish_at:
        print(f"scheduled: {args.at} {args.tz} ({publish_at})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
