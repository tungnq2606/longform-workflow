"""Shared helpers for the pipeline scripts. Every script takes the video folder as its first argument."""
import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(TOOLS, "kit")
if KIT not in sys.path:
    sys.path.insert(0, KIT)


def video_dir():
    if len(sys.argv) < 2:
        sys.exit("usage: %s channels/<id>/videos/NNN-slug [options]" % os.path.basename(sys.argv[0]))
    d = os.path.abspath(sys.argv[1])
    if not os.path.isdir(os.path.join(d, "script")):
        sys.exit("not a video folder (no script/): " + d)
    return d
