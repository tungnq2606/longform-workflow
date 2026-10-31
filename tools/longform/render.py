"""Render a long-form composition from a project's staged public dir (never the whole workspace).

  python -m tools.longform.render projects/000-spike Spike projects/000-spike/render/spike_1440p.mp4 [--frame 150] [--props '{"boil": true}']
"""
import argparse
import json
import os
import subprocess

from tools.longform import paths, stage

ANIM = os.path.join(paths.WS, "tools", "anim")
SPIKE_FILES = ["library/backgrounds/bach-dang-path-01.png", "library/characters/tran-hung-dao", "tools/kit/fonts/BeVietnamPro-ExtraBold.ttf"]


def command(composition, out, public, frame=None, props=None):
    if frame is not None:
        c = ["npx", "remotion", "still", "src/index.ts", composition, out, "--frame=%d" % frame]
    else:  # H.264 at 16 Mbps comes from tools/anim/remotion.config.ts (setting --crf as well is an error)
        c = ["npx", "remotion", "render", "src/index.ts", composition, out, "--codec=h264", "--audio-codec=aac"]
    c += ["--public-dir", public]
    if props:
        c.append("--props=%s" % json.dumps(props))
    return c


def type_check():
    """Regenerate kits.generated.ts and type-check the scenes: a pose the kit lacks fails here, not deep in a render."""
    py = os.path.join(paths.WS, ".venv", "bin", "python")
    for cmd, cwd in (([py, "-m", "tools.longform.kit", "ts"], paths.WS), (["npx", "tsc", "--noEmit", "-p", "."], ANIM)):
        if subprocess.run(cmd, cwd=cwd).returncode != 0:
            raise RuntimeError("type check failed: %s" % " ".join(cmd))


def render(project_dir, composition, out, files, frame=None, props=None):
    type_check()
    pub = os.path.abspath(stage.stage(project_dir, files))  # remotion runs in tools/anim: a relative path would miss
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    p = subprocess.run(command(composition, out, pub, frame, props), cwd=ANIM)
    if p.returncode != 0 or not os.path.exists(out):
        raise RuntimeError("remotion failed (exit %s)" % p.returncode)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("composition")
    ap.add_argument("out")
    ap.add_argument("--frame", type=int)
    ap.add_argument("--props")
    a = ap.parse_args()
    print(render(a.project, a.composition, a.out, SPIKE_FILES, a.frame, json.loads(a.props) if a.props else None))
