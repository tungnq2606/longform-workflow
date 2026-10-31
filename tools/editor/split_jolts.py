"""Smooth Veo's built-in jolts before assembling.

Veo clips jump slightly between source frames 63/64 and 127/128 (chunk seams). This
splits every clip of an assemble.swift spec at those frames and joins the two parts with
a short dissolve (pre-seam frames blend into post-seam frames), so the jump is spread
over a few frames instead of landing on one.

Usage: python3 split_jolts.py spec.json out_spec.json [--seams 64,128] [--blend 4]
"""
import argparse
import json

ap = argparse.ArgumentParser()
ap.add_argument("spec")
ap.add_argument("out")
ap.add_argument("--seams", default="64,128")
ap.add_argument("--blend", type=int, default=4)
args = ap.parse_args()

seams = [int(s) for s in args.seams.split(",")]
spec = json.load(open(args.spec))
clips = []
for c in spec["clips"]:
    # Keep each part long enough for its incoming blend plus a 12-frame outgoing dissolve
    # (overlapping audio ramps are rejected by AVFoundation).
    cuts = [s for s in seams if c["in"] + args.blend < s < c["out"] - (args.blend + 14)]
    edges = [c["in"]] + cuts + [c["out"]]
    for k in range(len(edges) - 1):
        part = dict(c, **{"in": edges[k], "out": edges[k + 1]})
        if k > 0:
            part["xfade"] = args.blend
            part.pop("freeze", None)
            part["note"] = f"seam smoothing at source frame {edges[k]}"
        clips.append(part)
spec["clips"] = clips
json.dump(spec, open(args.out, "w"), indent=2, ensure_ascii=False)
print(len(clips), "entries")
