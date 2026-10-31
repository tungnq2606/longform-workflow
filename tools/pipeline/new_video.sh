#!/bin/zsh
# Start a new video folder from the template:  tools/pipeline/new_video.sh median-worker 002 food-prices-since-2019
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
[[ -n "$1" && -n "$2" && -n "$3" ]] || { echo "usage: new_video.sh CHANNEL_ID NNN slug   (channels: $(ls $ROOT/channels | tr '\n' ' '))"; exit 1; }
[[ -f "$ROOT/channels/$1/channel.json" ]] || { echo "no channel: $1 (new channel: copy templates/channel to channels/<id>)"; exit 1; }
D="$ROOT/channels/$1/videos/$2-$3"
[[ -e "$D" ]] && { echo "exists: $D"; exit 1; }
mkdir -p "$ROOT/channels/$1/videos"
cp -R "$ROOT/templates/video" "$D"
sed -i '' "s/{{ID}}/$2/g; s/{{SLUG}}/$3/g" "$D/VIDEO.md"
echo "Created $D"
