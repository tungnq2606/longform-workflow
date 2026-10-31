#!/bin/bash
# YouTube upload and scheduling (YouTube Data API v3).
#   tools/youtube/yt.sh setup                    create .venv and install the Google client
#   tools/youtube/yt.sh auth CHANNEL_ID          one-time login; pick that channel in the Google screen
#   tools/youtube/yt.sh check VIDEO              dry run: validate upload/manifest.json, upload nothing
#   tools/youtube/yt.sh upload VIDEO             real upload (private, or scheduled if the manifest has publish_at)
# Make the manifest first: python3 tools/youtube/make_manifest.py VIDEO --at "YYYY-MM-DD HH:MM"
# Secrets: ~/.config/youtube-upload/client_secret.json (shared), token per channel in ~/.config/youtube-upload/<channel>/token.json
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$HERE/.venv/bin/python"
CONF="$HOME/.config/youtube-upload"

channel_of() {  # channels/<id>/videos/NNN-slug -> <id>
  local abs; abs="$(cd "$1" && pwd)"
  echo "$abs" | sed -n 's|.*/channels/\([^/]*\)/videos/.*|\1|p'
}

cmd="${1:-}"; shift || true
case "$cmd" in
  setup)
    python3 -m venv "$HERE/.venv"
    "$PY" -m pip install -q -r "$HERE/requirements.txt"
    echo "ok: $HERE/.venv" ;;
  auth)
    ch="${1:?channel id, e.g. fossil-receipts}"
    "$PY" "$HERE/youtube_auth.py" --client-secrets "$CONF/client_secret.json" --token-path "$CONF/$ch/token.json" ;;
  check|upload)
    v="${1:?VIDEO folder}"; ch="$(channel_of "$v")"
    [ -n "$ch" ] || { echo "not a channels/<id>/videos/<video> folder: $v" >&2; exit 2; }
    m="$v/upload/manifest.json"
    [ -f "$m" ] || { echo "missing $m; run make_manifest.py first" >&2; exit 2; }
    extra=()
    [ "$cmd" = upload ] && extra=(--execute --confirm-public)
    "$PY" "$HERE/youtube_upload.py" --manifest "$m" \
      --client-secrets "$CONF/client_secret.json" --token-path "$CONF/$ch/token.json" "${extra[@]+"${extra[@]}"}" ;;
  *) sed -n '2,8p' "$0"; exit 2 ;;
esac
