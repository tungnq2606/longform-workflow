#!/bin/bash
# Render an animated video with the Remotion toolkit (1440p, channel standard).
#
#   tools/anim/render.sh videos/NNN-slug            whole video  -> render/NNN-slug_1440p.mp4
#   tools/anim/render.sh videos/NNN-slug 3          voice block 3 only -> render/anim_block03_1440p.mp4 (test)
#   tools/anim/render.sh videos/NNN-slug studio     open Remotion Studio (live preview with scrubbing)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
V="$(cd "$1" && pwd)"
SLUG="$(basename "$V")"
python3 "$HERE/prep.py" "$V"
cd "$HERE"
if [ "$2" = "studio" ]; then
  exec npx remotion studio src/index.ts --public-dir="$V"
elif [ -n "$2" ]; then
  OUT="$V/render/anim_block$(printf %02d "$2")_1440p.mp4"
  npx remotion render src/index.ts Video "$OUT" --props="{\"block\":$2}" --public-dir="$V"
else
  OUT="$V/render/${SLUG}_1440p.mp4"
  npx remotion render src/index.ts Video "$OUT" --public-dir="$V"
fi
echo "done: $OUT"
