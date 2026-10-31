#!/usr/bin/env python3
"""Generate a video's images with Gemini through the Antigravity CLI (agy), one image per call.

Claude writes the prompts (tools/imageprompts/make_prompts.py -> images/prompts/manifest.json);
this runner hands each prompt to Gemini verbatim, then finds, checks and files the result itself.
It never trusts what the agent says about its work: files on disk decide.

Usage (VIDEO_DIR holds images/prompts/manifest.json):
  agy_images.py VIDEO_DIR                     generate everything still pending, in order
  agy_images.py VIDEO_DIR --only 01-03,01-04  just these ids        --limit N   at most N images this run
  agy_images.py VIDEO_DIR --workers 4         run up to 4 Gemini calls in parallel (default 3, max 8)
  agy_images.py VIDEO_DIR --dry-run           show what would run, call nothing
  agy_images.py VIDEO_DIR --no-flow           leave the key images (route "manual": sheets, key scenes) to the owner
                                              (default since 2026-10-28: they are made in Google Flow with Nano Banana Pro
                                              through gflow-cli, one at a time, when gflow is installed)
  agy_images.py VIDEO_DIR --redo ID           mark an image pending again (keeps old variants)
  agy_images.py VIDEO_DIR --approve ID [--variant N]   accept a sheet (copied to images/refs/) or pick a scene variant
  agy_images.py VIDEO_DIR --import ID FILE    use an image made by hand (Gemini app / Flow) instead
  agy_images.py VIDEO_DIR --compose           paste the approved model sheets into the cast sheet again
                                              (runs by itself when the last model sheet is approved)
  agy_images.py VIDEO_DIR --status            print the state table

Files: images/raw/ (every variant Gemini produced), images/refs/ (approved sheets), images/frames/
(2560x1440 PNG scenes for Remotion), images/runs/state.json (resume point) and images/runs/log.jsonl.
"""
import glob
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import flowcli  # noqa: E402  gflow-cli for the key images
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lessons  # noqa: E402  channel prompt lessons learnt from reviews
import preflight  # noqa: E402  Gemini's pre-generation prompt check

AGY = os.path.expanduser("~/.local/bin/agy")
BRAIN = os.path.expanduser("~/.gemini/antigravity-cli/brain")
MODEL = "gemini-4-argon-high"  # owner: Ultra plan quota is high, use the strongest model everywhere
ASPECTS = {
    "16:9": (2560, 1440, 1.70, 1.85),  # Nano Banana "16:9" is 43:24 = 1.79
    "9:16": (1440, 2560, 0.50, 0.62),  # Nano Banana "9:16" is 24:43 = 0.558
}
STOP_WORDS = ("quota", "credits balance", "resource_exhausted", "exhausted")

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


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def dims(path):
    out = run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path]).stdout
    w = re.search(r"pixelWidth: (\d+)", out)
    h = re.search(r"pixelHeight: (\d+)", out)
    return (int(w.group(1)), int(h.group(1))) if w and h else (0, 0)


def to_frame(src, dst, aspect="16:9"):
    """Cover-fit to target PNG (2560x1440 for 16:9, 1440x2560 for 9:16): scale then centre-crop."""
    fw, fh, _, _ = ASPECTS.get(aspect, ASPECTS["16:9"])
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".tmp.png"
    run(["sips", "-s", "format", "png", src, "--out", tmp])
    w, h = dims(tmp)
    s = max(fw / w, fh / h)
    run(["sips", "-z", str(round(h * s)), str(round(w * s)), tmp])
    run(["sips", "-c", str(fh), str(fw), tmp, "--out", dst])
    os.remove(tmp)
    return dims(dst) == (fw, fh)


def machine_check(path, aspect="16:9"):
    """Checks a machine can make on any image; style review happens later (Claude / owner)."""
    _, _, rmin, rmax = ASPECTS.get(aspect, ASPECTS["16:9"])
    problems = []
    if not os.path.exists(path) or os.path.getsize(path) < 30_000:
        problems.append("missing or too small to be a real image")
        return problems
    w, h = dims(path)
    if not w:
        problems.append("does not decode")
    elif not rmin <= w / h <= rmax:
        problems.append("aspect %.3f is not %s (%dx%d)" % (w / h, aspect, w, h))
    elif min(w, h) < 700:
        problems.append("too small (%dx%d)" % (w, h))
    return problems


def find_outputs(conv_id, name, since):
    """Generated files for this call: <brain>/<conversation>/<ImageName>_<ms>.<ext>, else paths named in transcripts."""
    found = set(glob.glob(os.path.join(BRAIN, conv_id, name + "_*.*")))
    logs = glob.glob(os.path.join(BRAIN, conv_id, ".system_generated", "logs", "transcript_full.jsonl"))
    for lg in logs:  # subagents write their own transcripts; follow them too
        txt = open(lg, encoding="utf-8", errors="ignore").read()
        for sub in set(re.findall(r'"conversationId\\?":\\?"([0-9a-f-]{36})', txt)):
            logs.append(os.path.join(BRAIN, sub, ".system_generated", "logs", "transcript_full.jsonl"))
        for p in re.findall(r"Generated image is saved at (/[^\s\"\\]+?\.(?:jpg|jpeg|png|webp))", txt):
            found.add(p)
        if len(logs) > 20:
            break
    return sorted(p for p in found if os.path.exists(p) and os.path.getmtime(p) >= since - 5
                  and os.path.splitext(p)[1].lower() in (".jpg", ".jpeg", ".png", ".webp"))


class Video:
    def __init__(self, vdir):
        self.img = os.path.join(os.path.abspath(vdir), "images")
        man = os.path.join(self.img, "prompts", "manifest.json")
        if not os.path.exists(man):
            sys.exit("no %s: run tools/imageprompts/make_prompts.py first" % man)
        self.manifest = json.load(open(man, encoding="utf-8"))
        self.aspect = self.manifest.get("aspect", "16:9")
        self.items = {i["id"]: i for i in self.manifest["items"]}
        self.runs = os.path.join(self.img, "runs")
        os.makedirs(self.runs, exist_ok=True)
        self.state_path = os.path.join(self.runs, "state.json")
        self.state = json.load(open(self.state_path)) if os.path.exists(self.state_path) else {}
        self.dirty = set()  # item ids this process changed; save() writes only these
        for d in ("raw", "refs", "frames"):
            os.makedirs(os.path.join(self.img, d), exist_ok=True)
        self.work = os.path.join(self.runs, "agy_workspace")  # isolated folder the worker runs in
        if not os.path.isdir(os.path.join(self.work, ".git")):
            os.makedirs(self.work, exist_ok=True)
            run(["git", "init", "-q", self.work])

    lock = threading.Lock()  # workers share one state file and one log

    def save(self):
        """Write only the items this process touched, merged into the file under a cross-process lock.
        Several runs (bulk fix, single redo, dashboard confirm) share state.json; writing the whole dict lost their updates."""
        with self.lock, open(self.state_path + ".lock", "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            disk = json.load(open(self.state_path)) if os.path.exists(self.state_path) else {}
            for k in self.dirty:
                disk[k] = self.state[k]
            for k, val in disk.items():
                if k not in self.dirty:
                    self.state[k] = val
            tmp = self.state_path + ".tmp"
            json.dump(disk, open(tmp, "w"), indent=1)
            os.replace(tmp, self.state_path)

    def log(self, **rec):
        rec["at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with self.lock, open(os.path.join(self.runs, "log.jsonl"), "a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def st(self, iid):
        self.dirty.add(iid)
        return self.state.setdefault(iid, {"status": "pending", "variants": [], "attempts": 0})

    # ------------------------------------------------------------ generation
    def ref_path(self, r):
        """Scenes get the cast sheet without its bottom row: Gemini copied the labelled expression heads into scenes."""
        p = os.path.join(self.img, r)
        if not os.path.basename(r).startswith("cast_sheet") or not os.path.exists(p):
            return p
        crop = p[:-4] + "_figures.png"
        with self.lock:
            if not os.path.exists(crop) or os.path.getmtime(crop) < os.path.getmtime(p):
                run([os.path.join(os.path.dirname(os.path.abspath(__file__)), "croptop"), p, crop, "0.79"])
        return crop

    def ready(self, it):
        missing = [r for r in it["refs"] if not os.path.exists(os.path.join(self.img, r))]
        return missing

    def generate(self, it, model, dry):
        s = self.st(it["id"])
        missing = self.ready(it)
        if missing:
            return "blocked: needs %s (approve the sheet or generate the previous scene first)" % ", ".join(missing)
        prompt = open(os.path.join(self.img, it["prompt_file"]), encoding="utf-8").read().strip()
        vdir = os.path.dirname(self.img)
        fixes = preflight.fixes_for(vdir, it["id"], prompt)  # Gemini's pre-generation check of this exact prompt
        rv = json.load(open(os.path.join(self.runs, "review.json"))).get(it["id"]) if os.path.exists(os.path.join(self.runs, "review.json")) else None
        if rv and rv.get("score", 5) < 5:  # redo after a review below 5: tell Gemini what was wrong with the last version
            prompt += "\nCORRECTION (the previous version was rejected): %s%s" % (
                "Avoid: " + "; ".join(rv.get("problems", [])) + ". " if rv.get("problems") else "", rv.get("fix", ""))
        prompt = lessons.with_rules(vdir, prompt, "image", fixes)  # the channel's lessons + the pre-flight fixes
        name = re.sub(r"[^a-z0-9_]", "_", ("%s_%03d_%s" % (self.manifest["video"], it["seq"], it["id"])).lower())
        paths = [os.path.abspath(self.ref_path(r) if it["kind"] == "scene" else os.path.join(self.img, r)) for r in it["refs"]]
        if it.get("route") == "manual":
            return self.generate_flow(it, s, prompt, paths, dry)
        path_line = ("- ImagePaths: [%s] (in this order)\n" % ", ".join('"%s"' % p for p in paths)) if paths else ""
        task = PREAMBLE.format(aspect=self.aspect, name=name, paths=path_line, prompt=prompt)
        if dry:
            return "would generate (%d refs, prompt %d chars)" % (len(paths), len(prompt))
        t0 = time.time()
        for attempt in range(3):
            s["attempts"] += 1
            p = run([AGY, "-p", task, "--model", model, "--output-format", "json", "--print-timeout", "600s"],
                    cwd=self.work, timeout=900)
            res = {}
            try:
                res = json.loads(p.stdout[p.stdout.find("{"):]) if "{" in p.stdout else {}
            except ValueError:
                pass
            conv = res.get("conversation_id", "")
            err = (p.stderr or "")[-600:]
            outs = find_outputs(conv, name, t0) if conv else []
            self.log(id=it["id"], attempt=attempt + 1, exit=p.returncode, conversation=conv, files=outs,
                     seconds=round(time.time() - t0, 1), usage=res.get("usage"), denied=res.get("denied_actions"), stderr=err[-300:])
            if outs:
                break
            if any(w in err.lower() for w in STOP_WORDS):
                s["status"] = "pending"
                return "stopped: Gemini quota or credits exhausted. Try again after the plan quota refreshes. " + err[-200:]
            time.sleep(20 * (attempt + 1))
        if not outs:
            s["status"] = "failed"
            s["last_error"] = err or "no image file found"
            return "failed: " + s["last_error"][-200:]
        for src in outs:  # the image subagent may retry; keep every variant
            k = len(s["variants"]) + 1
            dst = os.path.join(self.img, "raw", "%03d_%s_v%d%s" % (it["seq"], it["id"], k, os.path.splitext(src)[1].lower()))
            shutil.copy2(src, dst)
            s["variants"].append({"file": os.path.relpath(dst, self.img), "source": src, "conversation": conv,
                                  "problems": machine_check(dst, self.aspect)})
        s["chosen"] = len(s["variants"])
        return self.promote(it, s)

    def generate_flow(self, it, s, prompt, paths, dry):
        """Key image in Google Flow with Nano Banana Pro (gflow image i2i / t2i). Images use Flow's daily
        image quota, not Veo credits. flowcli serialises the calls and pauses between them."""
        if dry:
            return "would generate in Flow, nano-pro (%d refs, prompt %d chars)" % (len(paths), len(prompt))
        out_dir = os.path.join(self.runs, "flow_out", it["id"])
        os.makedirs(out_dir, exist_ok=True)
        aspect = self.aspect if self.aspect in ("9:16", "16:9", "1:1", "4:3", "3:4") else "16:9"
        args = (["image", "i2i", prompt] + [x for r in paths for x in ("--ref", r)]) if paths else ["image", "t2i", prompt]
        args += ["--model", "nano-pro", "--aspect", aspect, "--out", out_dir, "--json"]
        t0 = time.time()
        s["attempts"] += 1
        p, res, secs = flowcli.call(args)
        outs = sorted(f for f in glob.glob(os.path.join(out_dir, "**", "*"), recursive=True)
                      if os.path.getmtime(f) >= t0 - 5 and os.path.splitext(f)[1].lower() in (".png", ".jpg", ".jpeg", ".webp"))
        err = ((p.stderr or "") + "\n" + (p.stdout or ""))[-600:]
        self.log(id=it["id"], backend="flow", exit=p.returncode, files=outs, seconds=secs, stderr=err[-300:] if not outs else "")
        if not outs:
            s["status"] = "failed"
            s["last_error"] = "Flow (gflow exit %s): %s" % (p.returncode, err.strip()[-300:])
            return "failed: " + s["last_error"][-200:]
        for src in outs:
            k = len(s["variants"]) + 1
            dst = os.path.join(self.img, "raw", "%03d_%s_v%d%s" % (it["seq"], it["id"], k, os.path.splitext(src)[1].lower()))
            shutil.move(src, dst)
            s["variants"].append({"file": os.path.relpath(dst, self.img), "source": "flow:nano-pro", "conversation": "flow",
                                  "problems": machine_check(dst, self.aspect)})
        s["chosen"] = len(s["variants"])
        return self.promote(it, s)

    def promote(self, it, s):
        v = s["variants"][s["chosen"] - 1]
        src = os.path.join(self.img, v["file"])
        if v["problems"]:
            s["status"] = "check_failed"
            return "check failed: " + "; ".join(v["problems"])
        if it["kind"] == "scene":  # scenes go straight to the frame folder; the owner can still redo them
            ok = to_frame(src, os.path.join(self.img, it["save_as"]), self.aspect)
            fw, fh, _, _ = ASPECTS.get(self.aspect, ASPECTS["16:9"])
            s["status"] = "done" if ok else "check_failed"
            return "frame %s" % it["save_as"] if ok else ("could not convert to %dx%d" % (fw, fh))
        s["status"] = "needs_approval"  # sheets are references for everything after them: a person approves
        return "sheet ready for review: %s (approve with --approve %s)" % (v["file"], it["id"])

    # ------------------------------------------------------------ owner actions
    def approve(self, iid, variant=None):
        it, s = self.items[iid], self.st(iid)
        if variant:
            s["chosen"] = variant
        if not s.get("variants"):
            sys.exit("nothing to approve for %s" % iid)
        src = os.path.join(self.img, s["variants"][s["chosen"] - 1]["file"])
        dst = os.path.join(self.img, it["save_as"])
        if it["kind"] == "scene":
            to_frame(src, dst, self.aspect)
        else:
            run(["sips", "-s", "format", "png", src, "--out", dst])
        s["status"] = "approved"
        self.log(id=iid, action="approve", variant=s["chosen"])
        print("%s approved -> %s" % (iid, it["save_as"]))
        if it["kind"] == "model_sheet":
            self.compose_cast(quiet=True)

    def compose_cast(self, quiet=False):
        """The cast sheet is never generated: paste the approved model sheets together and approve the result."""
        it = next((i for i in self.manifest["items"] if i.get("route") == "compose"), None)
        if not it:
            return
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "imageprompts"))
        from compose_cast_sheet import compose
        try:
            sheet, figures = compose(os.path.dirname(self.img))
        except ValueError as e:
            if not quiet:
                sys.exit("cast sheet not composed: %s" % e)
            print("cast sheet waits: %s" % e)
            return
        self.import_file(it["id"], sheet)
        self.approve(it["id"])
        # the scene reference without expression heads; written after the sheet so ref_path() keeps it
        shutil.copy2(figures, os.path.join(self.img, "refs", "cast_sheet_figures.png"))
        os.utime(os.path.join(self.img, "refs", "cast_sheet_figures.png"))

    def import_file(self, iid, path):
        it, s = self.items[iid], self.st(iid)
        k = len(s["variants"]) + 1
        dst = os.path.join(self.img, "raw", "%03d_%s_v%d%s" % (it["seq"], iid, k, os.path.splitext(path)[1].lower()))
        shutil.copy2(path, dst)
        s["variants"].append({"file": os.path.relpath(dst, self.img), "source": os.path.abspath(path), "conversation": "manual",
                              "problems": machine_check(dst, self.aspect)})
        s["chosen"] = k
        print(iid, self.promote(it, s))

    def status(self):
        for i in self.manifest["items"]:
            s = self.state.get(i["id"], {})
            print("%3d %-14s %-12s %-15s variants=%d %s" % (i["seq"], i["id"], i["kind"], s.get("status", "pending"),
                                                           len(s.get("variants", [])), s.get("last_error", "")[:60]))


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    v = Video(a[0])

    def opt(flag, default=None):
        return a[a.index(flag) + 1] if flag in a else default
    if "--status" in a:
        return v.status()
    if "--approve" in a:
        v.approve(opt("--approve"), int(opt("--variant")) if "--variant" in a else None)
        return v.save()
    if "--import" in a:
        iid = a[a.index("--import") + 1]
        if v.items[iid].get("route") == "compose":
            sys.exit("%s is composed from the approved model sheets, never imported: use --compose" % iid)
        v.import_file(iid, a[a.index("--import") + 2])
        return v.save()
    if "--compose" in a:
        v.compose_cast()
        return v.save()
    if "--redo" in a:
        v.st(opt("--redo"))["status"] = "pending"
        return v.save()
    only = set(opt("--only").split(",")) if "--only" in a else None
    limit = int(opt("--limit", "0")) or None
    workers = max(1, min(8, int(opt("--workers", "3"))))
    model, dry = opt("--model", MODEL), "--dry-run" in a
    queue = []
    for it in v.manifest["items"]:
        s = v.st(it["id"])
        if only and it["id"] not in only:
            continue
        if not only and s["status"] != "pending":
            continue
        if it.get("route") == "compose":  # never generated, whatever the flags say
            if s["status"] != "approved":
                print("%3d %-14s composed from the model sheets once they are all approved" % (it["seq"], it["id"]), flush=True)
                break  # every scene uses it
            continue
        if it.get("route") == "manual" and not only and ("--no-flow" in a or not flowcli.available()):
            print("%3d %-14s made by hand (Google Flow, Nano Banana Pro): import it with --import" % (it["seq"], it["id"]), flush=True)
            if it["kind"] != "scene" and s["status"] != "approved":
                break  # everything after a sheet waits for it
            continue
        queue.append(it)
    if limit:
        queue = queue[:limit]
    if dry:
        for it in queue:
            print("%3d %-14s %s" % (it["seq"], it["id"], v.generate(it, model, True)), flush=True)
        return
    # Parallel scheduler: up to `workers` agy calls at once. An image whose reference is the previous scene's
    # frame waits until that frame exists; one whose reference can never appear is reported as blocked.
    makes = {i["save_as"]: i["id"] for i in queue}
    pending, running, stop = list(queue), {}, False
    print("%d images to make with %d parallel Gemini workers" % (len(queue), workers), flush=True)
    with ThreadPoolExecutor(workers) as ex:
        while pending or running:
            for it in list(pending):
                if stop or len(running) >= workers:
                    break
                missing = v.ready(it)
                coming = [r for r in missing if r in makes and makes[r] in {x["id"] for x in pending + list(running.values())}]
                if missing and len(coming) == len(missing):
                    continue  # waits for a scene that is still being made
                pending.remove(it)
                if missing:
                    print("%3d %-14s blocked: needs %s" % (it["seq"], it["id"], ", ".join(m for m in missing if m not in coming)), flush=True)
                    continue
                running[ex.submit(v.generate, it, model, False)] = it
            if not running:
                for it in pending:
                    print("%3d %-14s blocked: waits for an image that was not made" % (it["seq"], it["id"]), flush=True)
                break
            done_now, _ = wait(list(running), return_when=FIRST_COMPLETED)
            for f in done_now:
                it = running.pop(f)
                try:
                    msg = f.result()
                except Exception as e:  # one broken item must not stop the others
                    msg = "failed: %s" % e
                    v.st(it["id"])["status"] = "failed"
                    v.st(it["id"])["last_error"] = str(e)
                print("%3d %-14s %s" % (it["seq"], it["id"], msg), flush=True)
                v.save()
                if msg.startswith("stopped"):
                    stop = True
                    pending.clear()
    v.save()


if __name__ == "__main__":
    main()
