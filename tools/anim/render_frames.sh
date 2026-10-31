#!/bin/bash
# Render a video made of generated images (images/frames/) at 1440p, channel standard.
#   tools/anim/render_frames.sh videos/NNN-slug      -> render/NNN-slug_1440p.mp4
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
V="$(cd "$1" && pwd)"
python3 "$HERE/prep_frames.py" "$V"
cd "$HERE"
OUT="$V/render/$(basename "$V")_1440p.mp4"
npx remotion render src/index.ts Frames "$OUT" --public-dir="$V" --port=3124
echo "done: $OUT"
