"""Generate one image with Gemini through the agy CLI (plan quota). Every image goes through agy (owner, 2026-10-31:
no gflow/Flow).

  generate(prompt, refs, out_dir, name, aspect="16:9") -> [saved paths]

Same contracts as tools/gemini/agy_images.py (preamble, output discovery, quota stop words), without sips.
"""
import glob
import json
import os
import re
import subprocess
import time

from PIL import Image

AGY = os.path.expanduser("~/.local/bin/agy")
BRAIN = os.path.expanduser("~/.gemini/antigravity-cli/brain")
MODEL = "gemini-4-argon-high"
STOP_WORDS = ("quota", "credits balance", "resource_exhausted", "exhausted")
EXTS = (".png", ".jpg", ".jpeg", ".webp")

PREAMBLE = """You are an image production worker. Call the image generation tool exactly once to create exactly one image, then stop.
Use exactly these tool arguments:
- Prompt: the text between <PROMPT> and </PROMPT>, copied verbatim. Do not shorten, rewrite, translate, summarise or add anything.
- AspectRatio: "{aspect}"
- ImageName: "{name}"
{paths}Do not write files, do not run commands, do not describe or inspect the result, do not generate a second image.
When the tool returns, reply with the single word DONE.

<PROMPT>
{prompt}
</PROMPT>"""


class QuotaExhausted(RuntimeError):
    pass


def agy_task(prompt, refs, name, aspect):
    path_line = ("- ImagePaths: [%s] (in this order)\n" % ", ".join('"%s"' % p for p in refs)) if refs else ""
    return PREAMBLE.format(aspect=aspect, name=name, paths=path_line, prompt=prompt)


def _agy_outputs(conv_id, name, since):
    found = set(glob.glob(os.path.join(BRAIN, conv_id, name + "_*.*")))
    logs = glob.glob(os.path.join(BRAIN, conv_id, ".system_generated", "logs", "transcript_full.jsonl"))
    for lg in logs:
        txt = open(lg, encoding="utf-8", errors="ignore").read()
        for sub in set(re.findall(r'"conversationId\\?":\\?"([0-9a-f-]{36})', txt)):
            logs.append(os.path.join(BRAIN, sub, ".system_generated", "logs", "transcript_full.jsonl"))
        found.update(re.findall(r"Generated image is saved at (/[^\s\"\\]+?\.(?:jpg|jpeg|png|webp))", txt))
        if len(logs) > 20:
            break
    return sorted(p for p in found if os.path.exists(p) and os.path.getmtime(p) >= since - 5 and p.lower().endswith(EXTS))


def _keep(src, out_dir, name, k):
    """Save as PNG in out_dir; returns the path."""
    dst = os.path.join(out_dir, "%s_v%d.png" % (name, k))
    Image.open(src).convert("RGB").save(dst)
    return dst


def generate(prompt, refs, out_dir, name, aspect="16:9"):
    os.makedirs(out_dir, exist_ok=True)
    refs = [os.path.abspath(r) for r in refs]
    start = len(glob.glob(os.path.join(out_dir, name + "_v*.png")))
    t0 = time.time()
    work = os.path.join(out_dir, "_agy")
    os.makedirs(work, exist_ok=True)
    task = agy_task(prompt, refs, name, aspect)
    err = ""
    for attempt in range(3):
        p = subprocess.run([AGY, "-p", task, "--model", MODEL, "--output-format", "json", "--print-timeout", "600s"],
                           cwd=work, capture_output=True, text=True, timeout=900)
        try:
            res = json.loads(p.stdout[p.stdout.find("{"):]) if "{" in p.stdout else {}
        except ValueError:
            res = {}
        conv = res.get("conversation_id", "")
        outs = _agy_outputs(conv, name, t0) if conv else []
        if outs:
            return [_keep(f, out_dir, name, start + i + 1) for i, f in enumerate(outs)]
        err = (p.stderr or "")[-600:]
        if any(w in err.lower() for w in STOP_WORDS):
            raise QuotaExhausted(err[-200:])
        time.sleep(20 * (attempt + 1))
    raise RuntimeError("agy made no image after 3 tries: " + err[-300:])
