#!/usr/bin/env python3
"""Dry-run or execute a manifest-driven YouTube upload."""

from __future__ import annotations

import argparse
import http.client
import json
import mimetypes
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from manifest import ManifestError, load_and_validate
from youtube_auth import authorize, resolve_paths

RETRIABLE_STATUS_CODES = {500, 502, 503, 504}
MAX_RETRIES = 8


def _video_body(manifest: dict[str, Any]) -> dict[str, Any]:
    snippet = manifest["snippet"]
    status = manifest["status"]
    body_snippet: dict[str, Any] = {
        "title": snippet["title"],
        "description": snippet["description"],
    }
    if snippet["tags"]:
        body_snippet["tags"] = snippet["tags"]
    if snippet["category_id"]:
        body_snippet["categoryId"] = snippet["category_id"]

    body_status: dict[str, Any] = {
        "privacyStatus": status["privacy_status"],
        "selfDeclaredMadeForKids": status["made_for_kids"],
        "containsSyntheticMedia": status["contains_synthetic_media"],
    }
    if status["publish_at"]:
        body_status["publishAt"] = status["publish_at"]
    return {"snippet": body_snippet, "status": body_status}


def _upload_video(youtube, manifest: dict[str, Any]) -> str:
    try:
        import httplib2
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:
        raise RuntimeError("missing Google API packages; install requirements.txt") from exc

    video_path = manifest["video_path"]
    mime, _ = mimetypes.guess_type(video_path)
    if not mime or not mime.startswith("video/"):
        mime = "application/octet-stream"
    request = youtube.videos().insert(
        part="snippet,status",
        body=_video_body(manifest),
        notifySubscribers=manifest["status"]["notify_subscribers"],
        media_body=MediaFileUpload(video_path, mimetype=mime, chunksize=-1, resumable=True),
    )

    retries = 0
    while True:
        try:
            progress, response = request.next_chunk()
            if progress:
                print(f"Upload progress: {progress.progress() * 100:.1f}%", file=sys.stderr)
            if response is not None:
                video_id = response.get("id")
                if not video_id:
                    raise RuntimeError(f"upload returned no video ID: {response!r}")
                return video_id
        except HttpError as exc:
            if exc.resp.status not in RETRIABLE_STATUS_CODES or retries >= MAX_RETRIES:
                raise
        except (
            OSError,
            ConnectionError,
            TimeoutError,
            httplib2.HttpLib2Error,
            http.client.NotConnected,
            http.client.IncompleteRead,
            http.client.ImproperConnectionState,
            http.client.ResponseNotReady,
            http.client.BadStatusLine,
        ):
            if retries >= MAX_RETRIES:
                raise
        delay = random.uniform(0, min(2**retries, 64))
        retries += 1
        print(f"Retrying upload in {delay:.1f}s ({retries}/{MAX_RETRIES})", file=sys.stderr)
        time.sleep(delay)


def _set_thumbnail(youtube, video_id: str, thumbnail_path: str) -> dict[str, Any]:
    from googleapiclient.http import MediaFileUpload

    mime, _ = mimetypes.guess_type(thumbnail_path)
    return youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(thumbnail_path, mimetype=mime, resumable=False),
    ).execute()


def _insert_playlist(youtube, video_id: str, playlist_id: str) -> dict[str, Any]:
    return youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        },
    ).execute()


def _log_result(result: dict[str, Any], manifest: dict[str, Any]) -> Path:
    configured = manifest["execution"]["result_log_dir"] or os.environ.get(
        "YOUTUBE_RESULT_LOG_DIR"
    )
    log_dir = Path(configured).expanduser() if configured else Path("~/.local/state/youtube-upload").expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = result.get("video_id") or "failed"
    path = log_dir / f"{stamp}-{suffix}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--execute", action="store_true", help="perform the upload")
    parser.add_argument(
        "--confirm-public",
        action="store_true",
        help="confirm public, unlisted, or scheduled publication",
    )
    parser.add_argument("--client-secrets")
    parser.add_argument("--token-path")
    args = parser.parse_args()

    try:
        manifest, warnings = load_and_validate(args.manifest)
    except (ManifestError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2

    risky_visibility = manifest["status"]["privacy_status"] != "private" or bool(
        manifest["status"]["publish_at"]
    )
    if not args.execute:
        print(
            json.dumps(
                {"ok": True, "mode": "dry-run", "manifest": manifest, "warnings": warnings},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if risky_visibility and not args.confirm_public:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "public, unlisted, or scheduled execution requires --confirm-public",
                    "manifest": manifest,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    client_secrets, token_path = resolve_paths(args.client_secrets, args.token_path)
    result: dict[str, Any] = {
        "ok": False,
        "mode": "execute",
        "video_id": None,
        "youtube_url": None,
        "privacy_status": manifest["status"]["privacy_status"],
        "publish_at": manifest["status"]["publish_at"],
        "thumbnail": {"requested": bool(manifest["assets"]["thumbnail_path"]), "ok": None},
        "playlist": {"requested": bool(manifest["assets"]["playlist_id"]), "ok": None},
        "warnings": warnings,
        "errors": [],
    }

    try:
        try:
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError("missing Google API packages; install requirements.txt") from exc
        credentials = authorize(client_secrets, token_path)
        youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
        video_id = _upload_video(youtube, manifest)
        result["video_id"] = video_id
        result["youtube_url"] = f"https://youtu.be/{video_id}"
        result["ok"] = True

        thumbnail_path = manifest["assets"]["thumbnail_path"]
        if thumbnail_path:
            try:
                _set_thumbnail(youtube, video_id, thumbnail_path)
                result["thumbnail"]["ok"] = True
            except Exception as exc:
                result["thumbnail"]["ok"] = False
                result["thumbnail"]["error"] = str(exc)
                result["errors"].append("thumbnail upload failed")

        playlist_id = manifest["assets"]["playlist_id"]
        if playlist_id:
            try:
                response = _insert_playlist(youtube, video_id, playlist_id)
                result["playlist"]["ok"] = True
                result["playlist"]["playlist_item_id"] = response.get("id")
            except Exception as exc:
                result["playlist"]["ok"] = False
                result["playlist"]["error"] = str(exc)
                result["errors"].append("playlist insertion failed")
    except Exception as exc:
        result["errors"].append(str(exc))

    try:
        result["result_log_path"] = str(_log_result(result, manifest))
    except Exception as exc:
        result["errors"].append(f"result log failed: {exc}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] and not result["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
