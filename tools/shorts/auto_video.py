#!/usr/bin/env python3
"""The one button for a Shorts video's pictures: images, then clips, with the owner only approving.

  1. tools/gemini/auto_images.py: make every missing image (agy, and key images in Flow), Gemini review,
     redo 1-2/5 by itself; 3-4/5 wait for the owner.
  2. tools/shorts/flow_clips.py: every shot whose image passed (5/5 or approved) goes veo-lite test ->
     veo-fast (active shots) -> 1080p; it keeps rescanning, so approvals made while it runs join in.

Usage: auto_video.py VIDEO_DIR
Telegram reports what waits for the owner at the end of each step.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(os.path.dirname(HERE))


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    vdir = os.path.abspath(sys.argv[1])
    print("== step 1/2: images", flush=True)
    subprocess.run([sys.executable, "-u", os.path.join(WS, "tools", "gemini", "auto_images.py"), vdir], cwd=WS)
    print("\n== step 2/2: clips", flush=True)
    return subprocess.run([sys.executable, "-u", os.path.join(HERE, "flow_clips.py"), vdir], cwd=WS).returncode


if __name__ == "__main__":
    sys.exit(main())
