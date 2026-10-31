#!/usr/bin/env python3
"""Load, normalize, and validate YouTube upload manifests."""

from __future__ import annotations

import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ManifestError(ValueError):
    """Raised when a manifest cannot be safely used."""


def _load_yaml_or_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        try:
            import yaml
        except ImportError as exc:
            raise ManifestError(
                "PyYAML is required for YAML manifests; install requirements.txt"
            ) from exc
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ManifestError("manifest root must be a mapping")
    return data


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ManifestError(f"{name} must be a mapping")
    return value


def _required_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ManifestError(f"{name} must be explicitly set to true or false")
    return value


def _optional_bool(value: Any, name: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ManifestError(f"{name} must be true or false")
    return value


def _resolve_path(value: Any, base_dir: Path, name: str) -> Path | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ManifestError(f"{name} must be a path string")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _validate_text(text: str, name: str, limit: int, *, utf8_bytes: bool = False) -> None:
    length = len(text.encode("utf-8")) if utf8_bytes else len(text)
    unit = "UTF-8 bytes" if utf8_bytes else "characters"
    if length > limit:
        raise ManifestError(f"{name} exceeds {limit} {unit}")
    if "<" in text or ">" in text:
        raise ManifestError(f"{name} cannot contain '<' or '>'")


def _tag_length(tags: list[str]) -> int:
    return sum(len(tag) + (2 if " " in tag else 0) for tag in tags) + max(0, len(tags) - 1)


def _parse_publish_at(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ManifestError("status.publish_at must be an ISO 8601 string")
    candidate = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ManifestError("status.publish_at must be valid ISO 8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ManifestError("status.publish_at must include a timezone offset")
    if parsed <= datetime.now(timezone.utc):
        raise ManifestError("status.publish_at must be in the future")
    return parsed.isoformat()


def load_and_validate(path: str | Path) -> tuple[dict[str, Any], list[str]]:
    manifest_path = Path(path).expanduser().resolve()
    if not manifest_path.is_file():
        raise ManifestError(f"manifest not found: {manifest_path}")

    raw = _load_yaml_or_json(manifest_path)
    base_dir = manifest_path.parent
    snippet = _mapping(raw.get("snippet"), "snippet")
    status = _mapping(raw.get("status"), "status")
    assets = _mapping(raw.get("assets"), "assets")
    execution = _mapping(raw.get("execution"), "execution")

    video_path = _resolve_path(raw.get("video_path"), base_dir, "video_path")
    if video_path is None or not video_path.is_file():
        raise ManifestError(f"video_path is not a file: {video_path}")

    title = snippet.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ManifestError("snippet.title is required")
    title = title.strip()
    _validate_text(title, "snippet.title", 100)

    description = snippet.get("description", "")
    if not isinstance(description, str):
        raise ManifestError("snippet.description must be a string")
    _validate_text(description, "snippet.description", 5000, utf8_bytes=True)

    tags = snippet.get("tags", [])
    if tags is None:
        tags = []
    if not isinstance(tags, list) or not all(isinstance(tag, str) and tag.strip() for tag in tags):
        raise ManifestError("snippet.tags must be a list of non-empty strings")
    tags = [tag.strip() for tag in tags]
    if _tag_length(tags) > 500:
        raise ManifestError("snippet.tags exceeds YouTube's 500-character accounting limit")

    category_id = snippet.get("category_id")
    if category_id is not None:
        category_id = str(category_id)
        if not category_id.isdigit():
            raise ManifestError("snippet.category_id must be numeric")

    privacy = status.get("privacy_status", "private")
    if privacy not in {"private", "unlisted", "public"}:
        raise ManifestError("status.privacy_status must be private, unlisted, or public")
    publish_at = _parse_publish_at(status.get("publish_at"))
    if publish_at and privacy != "private":
        raise ManifestError("scheduled uploads require status.privacy_status: private")

    made_for_kids = _required_bool(status.get("made_for_kids"), "status.made_for_kids")
    synthetic = _required_bool(
        status.get("contains_synthetic_media"), "status.contains_synthetic_media"
    )
    notify = _optional_bool(status.get("notify_subscribers"), "status.notify_subscribers", False)

    thumbnail_path = _resolve_path(assets.get("thumbnail_path"), base_dir, "assets.thumbnail_path")
    if thumbnail_path is not None:
        if not thumbnail_path.is_file():
            raise ManifestError(f"thumbnail is not a file: {thumbnail_path}")
        if thumbnail_path.stat().st_size > 2 * 1024 * 1024:
            raise ManifestError("thumbnail exceeds YouTube's 2 MB limit")
        mime, _ = mimetypes.guess_type(thumbnail_path.name)
        if mime not in {"image/jpeg", "image/png"}:
            raise ManifestError("thumbnail must be a JPEG or PNG file")

    playlist_id = assets.get("playlist_id")
    if playlist_id is not None and (not isinstance(playlist_id, str) or not playlist_id.strip()):
        raise ManifestError("assets.playlist_id must be a non-empty string or null")

    result_log_dir = _resolve_path(
        execution.get("result_log_dir"), base_dir, "execution.result_log_dir"
    )

    warnings: list[str] = []
    if privacy != "private":
        warnings.append(f"upload visibility is {privacy}")
    if publish_at:
        warnings.append(f"video is scheduled to publish at {publish_at}")
    if notify:
        warnings.append("subscriber notifications are enabled")

    normalized = {
        "manifest_path": str(manifest_path),
        "video_path": str(video_path),
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "category_id": category_id,
        },
        "status": {
            "privacy_status": privacy,
            "publish_at": publish_at,
            "made_for_kids": made_for_kids,
            "contains_synthetic_media": synthetic,
            "notify_subscribers": notify,
        },
        "assets": {
            "thumbnail_path": str(thumbnail_path) if thumbnail_path else None,
            "playlist_id": playlist_id.strip() if isinstance(playlist_id, str) else None,
        },
        "execution": {
            "result_log_dir": str(result_log_dir) if result_log_dir else None,
        },
    }
    return normalized, warnings
