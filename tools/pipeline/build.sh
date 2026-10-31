#!/bin/zsh
# One command after script/audio/scenes change:  tools/pipeline/build.sh videos/NNN-slug
# Channel standard: 1440p (2560x1440, ~16 Mbps). Add "1080" to also render a 1080p copy.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
V="$(cd "$1" && pwd)"
python3 "$HERE/frames.py" "$V"            # 1440p frames + timing
python3 "$HERE/review.py" "$V"
python3 "$HERE/project.py" "$V"
[[ -x "$HERE/../editor/render" ]] || swiftc -O "$HERE/../editor/render.swift" -o "$HERE/../editor/render"
cd "$V/render"
"$HERE/../editor/render" project.json 2>&1 | grep -v -E "^frame [0-9]"
if [[ "$2" == "1080" ]]; then
  python3 "$HERE/frames.py" "$V" --width 1920
  "$HERE/../editor/render" project_1080p.json 2>&1 | grep -v -E "^frame [0-9]"
fi
echo "Done: $V/render/"
