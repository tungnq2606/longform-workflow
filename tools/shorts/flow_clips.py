#!/usr/bin/env python3
"""Make the Veo clips of a 9:16 Shorts video in Google Flow through gflow-cli, one clip at a time.

Each shot goes through these stages (owner rule, 2026-10-28):
  lite     veo-lite test clip -> clips/_test/<ID>.lite.mp4, reviewed by Gemini
  fast     active shots only: veo-fast clip once the test is accepted -> clips/<ID>.mp4, reviewed again
           (ambient shots keep the accepted veo-lite clip as their final clip)
  upscale  Flow's 1080p upscale of the accepted clip replaces clips/<ID>.mp4 (720p kept as <ID>.720p.mp4)
After every review (score 1-5): 4-5 moves on; 3 waits for the owner (dashboard "Duyệt" / "Làm lại");
1-2 is made again up to 5 times per stage, each time with a motion prompt Gemini rewrites against the problems
of the clip that just failed; still failing, an active shot keeps its passing veo-lite clip, otherwise the still image is used.

The start image must be 5/5 in images/runs/review.json or approved by the owner in images/runs/approvals.json
(both for its current file); an image that waits for a decision is never sent (only Veo spends credits).

Usage:
  flow_clips.py VIDEO_DIR                  every shot with a veo_prompt (ambient and active) that is ready and not finished
  flow_clips.py VIDEO_DIR --only S06A,S07B just these ids
  flow_clips.py VIDEO_DIR --approve ID     owner accepts the clip waiting at its stage (then run again)
  flow_clips.py VIDEO_DIR --redo ID        owner wants the waiting stage made again (with the review's fix)
  flow_clips.py VIDEO_DIR --skip-review    also use start images Gemini has not reviewed yet
  flow_clips.py VIDEO_DIR --status | --dry-run

Account safety (gflow-cli ACCOUNT_SAFETY.md: Flow's WAF reacts to cumulative cadence): strictly one clip at a
time, a random 30-75 s pause between Flow calls (Gemini reviews the last clip meanwhile), one Flow project per video (images/runs/flow.json), and the
batch stops at the first gflow failure instead of retrying into a block.

Files: images/runs/flow_state.json (stage per shot), images/runs/flow_clips.jsonl (one line per gflow call).
"""
import argparse
import calendar
import concurrent.futures as cf
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import review_video  # noqa: E402
import notify  # noqa: E402  Telegram, no-op when not configured
import workqueue  # noqa: E402  owner decisions queued on disk
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gemini"))
import lessons  # noqa: E402  channel prompt lessons learnt from reviews
import flowcli  # noqa: E402  serialised, paced gflow calls

MODELS = {"lite": "veo-lite", "fast": "veo-fast"}
NEXT = {"lite": "fast", "fast": "upscale", "upscale": "done"}
# exit codes from gflow-cli: stop the whole batch, never retry these
STOP_CODES = {98: "too many steps for one shot (script safety cap)", 99: "gflow reported success but no file was found",
              10: "Google WAF / reCAPTCHA block (profile cooling down: wait ~30 min)",
              21: "daily or per-minute quota reached", 22: "plan/tier refused the model",
              23: "Flow UI changed or model unavailable (gflow-cli needs an update)",
              28: "Flow editor unreachable", 27: "Flow did not accept the start-image upload in time (nothing billed)",
              15: "the automation browser closed (nothing billed)", 100: "the 1080p export was not ready in time (no credits; retried)", 7: "a paid clip could not be downloaded yet (kept, will be fetched)"}
# What a failure means for the rest of the run (the dashboard reconciler acts on "last_error" in auto.json):
#   transient: nothing billed, worth another try in a few minutes; waf: Google cool-down (~30 min);
#   hard: needs the owner (quota, plan, Flow UI changed, unknown).
FAIL_KIND = {100: "transient", 27: "transient", 15: "transient", 28: "transient", 99: "transient", 98: "hard",
             10: "waf", 21: "hard", 22: "hard", 23: "hard"}
FAST_TRIES_OVER_LITE = 2  # veo-fast failures at 1-2/5 before the shot keeps its passing veo-lite clip (2026-10-30)
REWRITE_AFTER = 1  # failed tries of a stage before Gemini rewrites its motion prompt (owner, 2026-10-29: from the first)
PASS = 4  # lowest review score accepted without the owner (2026-10-29; was 5): 3 asks, 1-2 redo
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def load_json(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


def find_key(res, names, test=lambda v: isinstance(v, str) and v):
    """First value under one of `names` anywhere in gflow's JSON result."""
    if isinstance(res, dict):
        for k, v in res.items():
            if k in names and test(v):
                return v
        res = list(res.values())
    if isinstance(res, list):
        for v in res:
            found = find_key(v, names, test)
            if found:
                return found
    return None


class Flow:
    def __init__(self, vdir, args):
        self.vdir, self.args = vdir, args
        self.img = os.path.join(vdir, "images")
        self.runs = os.path.join(self.img, "runs")
        self.state_p = os.path.join(self.runs, "flow_state.json")
        self.state = load_json(self.state_p, {})
        self.flow_p = os.path.join(self.runs, "flow.json")
        self.flow = load_json(self.flow_p, {})
        self.shots = {s["id"]: s for s in load_json(os.path.join(self.img, "shots.json"), {}).get("shots", [])}
        self.aspect = "16:9" if load_json(os.path.join(self.img, "shots.json"), {}).get("aspect") == "16:9" else "9:16"
        self.items = [i for i in load_json(os.path.join(self.img, "prompts", "manifest.json"), {"items": []})["items"]
                      if i["kind"] == "scene"]
        self.events = []  # what this run did, per shot, for the Telegram summary
        self.credits, self.credits_at = None, 0  # last Flow balance read, and when
        # Gemini reviews finished clips on side threads, several at once, while Flow makes the next one (Flow itself
        # stays one call at a time); review_video merges each result into clip_review.json under a file lock
        self.pool = cf.ThreadPoolExecutor(max_workers=3)
        self.reviewing = {}  # sid -> future
        self.lock = threading.Lock()

    def save(self):
        with self.lock:
            for _ in range(5):  # the review thread may touch its own shot's entry while this one is written
                try:
                    return save_json(self.state_p, json.loads(json.dumps(self.state)))
                except RuntimeError:
                    time.sleep(0.05)

    def review_later(self, sid, stage):
        """Queue the Gemini review of this clip and go on with other shots; needs_review lets a new run redo it."""
        self.st(sid)["needs_review"] = True
        self.save()
        self.reviewing[sid] = self.pool.submit(self.review, sid, stage)

    def harvest(self, wait=False):
        """Shots whose review has finished (all of them with wait=True): their next step is known again."""
        if wait and self.reviewing:
            cf.wait(list(self.reviewing.values()), return_when=cf.FIRST_COMPLETED)
        done = [sid for sid, fu in self.reviewing.items() if fu.done()]
        for sid in done:
            err = self.reviewing.pop(sid).exception()
            if err:
                self.st(sid).update(status="ask", note="Gemini review crashed (%s): check the clip yourself" % err)
                print("%s review crashed: %s" % (sid, err), flush=True)
            self.save()
        return done

    def drain(self):
        while self.reviewing:
            self.harvest(wait=True)

    def st(self, sid):
        return self.state.setdefault(sid, {"stage": "lite", "status": "todo", "tries": {}})

    def paths(self, sid):
        c = os.path.join(self.vdir, "clips")
        return {"lite": os.path.join(c, "_test", sid + ".lite.mp4"), "fast": os.path.join(c, sid + ".mp4")}

    def log(self, rec):
        rec["at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(os.path.join(self.runs, "flow_clips.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ---------------------------------------------------------------- start image gate
    def end_frame(self, sid):
        """Path of the shot's end frame when shots.json sets "end_frame" (a shot id or a path under images/)
        and the file exists; None for a normal first-frame-only shot."""
        ref = self.shots.get(sid, {}).get("end_frame")
        if not ref:
            return None
        it = next((i for i in self.items if i["id"] == ref), None)
        p = os.path.join(self.img, it["save_as"] if it else ref)
        return p if os.path.exists(p) else None

    def image_block(self, it):
        """Why this shot's start image may not go to Veo yet, or None."""
        src = os.path.join(self.img, it["save_as"])
        if not os.path.exists(src):
            return "no image yet"
        appr = load_json(os.path.join(self.runs, "approvals.json"), {}).get("images", {}).get(it["id"])
        if appr and abs(appr.get("mtime", 0) - os.path.getmtime(src)) < 1:
            return None
        r = load_json(os.path.join(self.runs, "review.json"), {}).get(it["id"])
        if not r or abs(r.get("mtime", 0) - os.path.getmtime(src)) >= 1:
            return None if self.args.skip_review else "image not reviewed yet"
        if r.get("score", 0) < PASS:
            return "image %s/5 waits for your decision (or a redo)" % r.get("score")
        return None

    # ---------------------------------------------------------------- gflow calls
    def gflow(self, cmd):
        lo, hi = (int(x) for x in self.args.gap.split("-"))
        p, res, secs = flowcli.call(cmd, gap=(lo, hi))
        return p, res, secs, ((p.stderr or "") + "\n" + (p.stdout or "")).strip()[-1500:]

    def generate(self, sid, stage):
        it_shot = self.shots[sid]
        s = self.st(sid)
        # the manifest's clip prompt carries the video's clip rules and sound line (make_shorts_prompts.py); a prompt
        # Gemini rewrote after a failed clip is motion only, so the same rules go after it
        item = next((i for i in self.items if i["id"] == sid), {})
        override = self.override(sid, stage)
        if override:
            rules = item.get("veo_rules", "")
            prompt = override.strip().rstrip(".") + (". " + rules if rules else "")
        else:
            prompt = (item.get("veo_prompt") or it_shot.get("veo_prompt", "")).strip()
        fix = s.get("fix") if s.get("redo_fix") else None
        if fix:
            prompt += " " + fix
        prompt = lessons.with_rules(self.vdir, prompt, "clip")  # channel lessons from earlier clip reviews
        src = os.path.join(self.img, next(i for i in self.items if i["id"] == sid)["save_as"])
        dst = self.paths(sid)[stage]
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        tmp = dst[:-4] + ".part.mp4"
        if os.path.exists(tmp):
            os.remove(tmp)
        lost = s.get("unfetched")
        if lost and lost.get("stage") == stage:  # a clip of this stage was paid for but never downloaded
            print("[%s] %s: fetching the paid clip %s instead of generating again" % (sid, stage, lost["media_id"]), flush=True)
            res = self.download(lost["media_id"], tmp)
            if res:
                s.pop("unfetched", None)
                return self.accept(sid, stage, tmp, dst, res, 0)
            lost["rounds"] = lost.get("rounds", 0) + 1
            if lost["rounds"] < 2:
                self.save()
                return 7, "the paid clip %s still cannot be downloaded; it stays recorded, nothing was billed" % lost["media_id"]
            # 2 runs x 3 tries: Flow never produced a downloadable clip (failed or filtered render) -> make a new one
            print("[%s] Flow never delivered clip %s; generating a new one" % (sid, lost["media_id"]), flush=True)
            s.pop("unfetched", None)
            s["redo_fix"] = not self.rewrite_prompt(sid, stage)
            self.save()
        cmd = ["video", "i2v", "--initial-frame", src, prompt, "--aspect", self.aspect,
               "--model", MODELS[stage], "-o", tmp, "--json"]
        if self.end_frame(sid):  # 2-frame shot: Flow interpolates start -> end (small, local changes only)
            cmd += ["--end-frame", self.end_frame(sid)]
        cmd += ["--project", self.flow["project"]] if self.flow.get("project") else ["--project-name", os.path.basename(self.vdir)]
        print("[%s] %s with %s: %s" % (sid, stage, MODELS[stage], prompt[:100]), flush=True)
        # measured cost per clip (owner, 2026-10-30: show credits per video); a balance older than 5 min is read
        # again so spending outside this run is not counted
        fresh = self.credits is not None and time.time() - self.credits_at < 300
        before = self.credits if fresh else flowcli.balance()
        p, res, secs, err = self.gflow(cmd)
        self.credits, self.credits_at = flowcli.balance(), time.time()
        if p.returncode and not (os.path.exists(tmp) and os.path.getsize(tmp) > 0):
            # Flow may have finished (and billed) a clip gflow lost: download missed the 20 s grace (exit 7,
            # gflow-cli #871) or the run timed out while rendering (exit 9). If the catalog has it, fetch it, free.
            row = self.catalog_row(prompt, MODELS[stage], time.time() - secs - 60)
            res = (self.download(row["media_id"], tmp, row.get("project_id")) if row else None) or res
            if row and not res.get("recovered"):
                s["unfetched"] = {"stage": stage, "media_id": row["media_id"]}  # never pay for this clip again
                self.save()
        ok = (p.returncode == 0 or res.get("recovered")) and os.path.exists(tmp) and os.path.getsize(tmp) > 0
        spent = before - self.credits if before is not None and self.credits is not None else None
        self.log({"id": sid, "stage": stage, "ok": ok, "code": p.returncode, "seconds": secs, "result": res,
                  "credits_before": before, "credits_after": self.credits, "credits_spent": spent,
                  **({} if ok else {"error": err})})
        if not ok:
            return p.returncode or 99, err
        return self.accept(sid, stage, tmp, dst, res, secs, prompt)

    def accept(self, sid, stage, tmp, dst, res, secs, prompt=""):
        """A clip of this stage is on disk (generated now, or a paid clip fetched later): file it for review."""
        s = self.st(sid)
        if os.path.exists(dst):
            os.replace(dst, dst[:-4] + ".old.mp4")
        os.replace(tmp, dst)
        s["tries"][stage] = s["tries"].get(stage, 0) + 1
        s["needs_review"] = True  # a crash before the review must not pay for this clip again
        s["media_id"] = find_key(res, ("media_id", "mediaId", "media_uuid", "mediaUuid"),
                                 lambda v: isinstance(v, str) and bool(UUID_RE.match(v)))
        if not s["media_id"]:  # needed for the 1080p upscale
            row = self.catalog_row(prompt, MODELS[stage], time.time() - secs - 60) if prompt else None
            s["media_id"] = row and row.get("media_id")
        s.setdefault("media", {})[stage] = s["media_id"]
        if not self.flow.get("project"):
            pid = find_key(res, ("project_id", "projectId", "project"))
            if pid:
                self.flow["project"] = pid
                save_json(self.flow_p, self.flow)
        print("ok %s -> %s (%d s)" % (sid, os.path.relpath(dst, self.vdir), secs), flush=True)
        return 0, ""

    def catalog_row(self, prompt, model, t_submit):
        """gflow's local catalog entry of the clip just made from this prompt and model, or None."""
        env = flowcli.env()
        p = subprocess.run([flowcli.GFLOW, "data", "list", "videos", "--json", "--limit", "10"], capture_output=True, text=True, env=env)
        want = model.split("-")[-1]  # catalog says e.g. "veo_3_1_lite" for veo-lite
        for line in (p.stdout or "").splitlines():
            try:
                row = json.loads(line)
                made = calendar.timegm(time.strptime(row.get("created_at", "")[:19], "%Y-%m-%dT%H:%M:%S"))
            except ValueError:
                continue
            if row.get("prompt") == prompt and want in (row.get("model") or "") and made >= t_submit:
                return row
        return None

    def recover(self, prompt, model, tmp, t_submit):
        """Download the clip this run just paid for from Flow's catalog; returns a result dict or None."""
        env = flowcli.env()
        row = self.catalog_row(prompt, model, t_submit)
        if row:
            return self.download(row["media_id"], tmp, row.get("project_id"))
        print("recovery: clip not found in gflow's catalog", flush=True)
        return None

    def download(self, media_id, tmp, project_id=None, tries=3):
        """Fetch a clip Flow already made (and billed) by its media id: free, retried because Flow's clip page
        sometimes loads too slowly for gflow's window (exit 7, 'a slow load can miss the window')."""
        out_dir = os.path.join(os.path.dirname(tmp), "_dl")
        os.makedirs(out_dir, exist_ok=True)
        for n in range(1, tries + 1):
            print("fetching already-paid clip %s (try %d/%d, no credits)" % (media_id, n, tries), flush=True)
            t0 = time.time()
            d, _, _ = flowcli.call(["data", "download", media_id, "--out", out_dir], gap=(5, 15))  # opens Chrome too
            got = sorted((f for f in glob.glob(os.path.join(out_dir, "**", "*.mp4"), recursive=True) if os.path.getmtime(f) >= t0 - 5),
                         key=os.path.getmtime)
            if d.returncode == 0 and got:
                shutil.move(got[-1], tmp)
                return {"recovered": True, "media_id": media_id, "project_id": project_id}
            print("download failed (exit %s): %s" % (d.returncode, ((d.stderr or "") + (d.stdout or ""))[-200:]), flush=True)
        return None

    def upscale(self, sid):
        s = self.st(sid)
        dst = self.paths(sid)["fast"]
        if not s.get("media_id"):
            s.update(stage="done", status="done", note="720p only: gflow returned no media id to upscale")
            print("%s: no media id from gflow, kept the 720p clip" % sid, flush=True)
            return 0, ""
        out_dir = os.path.join(self.vdir, "clips", "_test", "up_" + sid)
        os.makedirs(out_dir, exist_ok=True)
        cmd = ["video", "upscale", s["media_id"], "--scale", "1080p", "-o", out_dir]
        if self.flow.get("project"):
            cmd += ["--project", self.flow["project"]]
        print("[%s] upscale 1080p" % sid, flush=True)
        p, res, secs, err = self.gflow(cmd)
        got = sorted(glob.glob(os.path.join(out_dir, "**", "*.mp4"), recursive=True), key=os.path.getmtime)
        ok = p.returncode == 0 and bool(got)
        self.log({"id": sid, "stage": "upscale", "ok": ok, "code": p.returncode, "seconds": secs, "result": res,
                  **({} if ok else {"error": err})})
        if not ok:
            return p.returncode or 99, err
        os.replace(dst, dst[:-4] + ".720p.mp4")
        shutil.move(got[-1], dst)
        s.update(stage="done", status="done")
        print("ok %s -> clips/%s.mp4 (1080p, %d s)" % (sid, sid, secs), flush=True)
        self.events.append((sid, "nâng 1080p xong ✓"))
        return 0, ""

    # ---------------------------------------------------------------- review + decision
    def review(self, sid, stage):
        path = self.paths(sid)[stage]
        review_video.review_clips(self.vdir, only=[sid], workers=1, paths={sid: path})
        r = load_json(os.path.join(self.runs, "clip_review.json"), {}).get(sid)
        s = self.st(sid)
        if not r or abs(r.get("mtime", 0) - os.path.getmtime(path)) >= 1:
            s.update(status="ask", note="Gemini review failed: check the clip yourself")
            return
        score = r.get("score", 0)
        s.update(score=score, problems=r.get("problems", []), fix=r.get("fix", ""), redo_fix=False, needs_review=False,
                 file=os.path.relpath(path, self.vdir))
        s.setdefault("history", []).append({"stage": stage, "score": score, "problems": r.get("problems", [])})
        n = s["tries"].get(stage, 0)
        if score >= PASS:
            s.update(stage=self.next_stage(sid, stage), status="todo", note="")
        elif score >= 3:
            s.update(status="ask", note="%s clip %d/5: approve or redo" % (stage, score))
        elif stage == "fast" and n >= FAST_TRIES_OVER_LITE and s.get("media", {}).get("lite") and os.path.exists(self.paths(sid)["lite"]):
            self.fallback(sid, stage, score)  # a passing veo-lite clip beats more veo-fast credits (S08B, 003)
        elif n <= self.args.max_redo:
            # owner, 2026-10-29: rewrite the motion prompt after EVERY failed clip, aimed at what just broke
            rewritten = n >= REWRITE_AFTER and self.rewrite_prompt(sid, stage)
            note = ("%s clip %d/5: Gemini rewrote the prompt for redo %d/%d" if rewritten else
                    "%s clip %d/5: redo %d/%d with the review's fix") % (stage, score, n, self.args.max_redo)
            s.update(status="todo", redo_fix=not rewritten, note=note)
        else:
            self.fallback(sid, stage, score)
        print("%s %s review %d/5 -> %s" % (sid, stage, score, s["status"] if s["status"] == "ask" else s["stage"]), flush=True)
        self.events.append((sid, "clip %s %d/5 → %s" % (stage, score, "đạt" if score >= PASS else
                                                         ("chờ bạn duyệt" if score >= 3 else "tự làm lại"))))

    def override(self, sid, stage):
        """The motion prompt Gemini rewrote for this stage; veo-fast starts from the one that passed at veo-lite
        (S08B, 003: fast went back to the base prompt that had failed 3 times at lite and failed again)."""
        po = self.st(sid).get("prompt_override", {})
        return po.get(stage) or (po.get("lite") if stage == "fast" else None)

    def rewrite_prompt(self, sid, stage):
        """After repeated 1-2/5 clips: Gemini rewrites the Veo motion prompt from everything the reviews rejected
        (fewer moving parts, simpler single action). Stored per stage; the shot's own prompt stays as written."""
        s, shot = self.st(sid), self.shots.get(sid, {})
        item = next((i for i in self.items if i["id"] == sid), {})
        current = self.override(sid, stage) or item.get("veo_motion") or shot.get("veo_prompt", "")
        last = s.get("history", [])[-1:] or [{"stage": stage, "score": s.get("score"), "problems": s.get("problems", [])}]
        task = ("A Veo image-to-video prompt just produced a clip that failed review. Rewrite the prompt so the next "
                "clip avoids EXACTLY what went wrong in the last clip (listed first), without bringing back earlier "
                "problems. Keep the same shot, story beat and camera; name what must stay still or keep its shape "
                "(e.g. 'banners stay attached to their poles', 'no new objects appear in the sky'); prefer one clear "
                "main action, slower motion, fewer moving parts; avoid fragile details that vanish or morph. English, "
                "under 70 words, motion only (the start image fixes the look).\n\n"
                "Prompt used for the failed clip: %s\nShot: %s\nLAST CLIP PROBLEMS (fix these): %s\nEarlier problems:\n%s"
                % (current, shot.get("camera", ""), "; ".join(last[0].get("problems", [])),
                   "\n".join("- %s %s/5: %s" % (h["stage"], h["score"], "; ".join(h["problems"])) for h in s.get("history", [])[-6:-1]) or "-"))
        try:
            data = lessons.run_agy_json(task, {"type": "object", "properties": {"prompt": {"type": "string"}, "why": {"type": "string"}},
                                               "required": ["prompt", "why"]}, os.path.join(self.runs, "agy_workspace"))
        except Exception as e:  # noqa: BLE001
            print("prompt rewrite failed (%s); retrying with the old prompt" % e, flush=True)
            return False
        s.setdefault("prompt_override", {})[stage] = data["prompt"].strip()
        print("%s: new motion prompt (%s): %s" % (sid, data["why"][:80], data["prompt"][:120]), flush=True)
        return True

    def fallback(self, sid, stage, score):
        """Out of tries at 1-2/5: never ask the owner to approve a broken clip. Active shot failing veo-fast keeps
        its passing veo-lite clip; a shot failing veo-lite is rendered from its still image."""
        s, lite, final = self.st(sid), self.paths(sid)["lite"], self.paths(sid)["fast"]
        if stage == "fast" and os.path.exists(lite) and s.get("media", {}).get("lite"):
            if os.path.exists(final):
                os.replace(final, final[:-4] + ".rejected.mp4")
            shutil.copy2(lite, final)
            s.update(stage="upscale", status="todo", media_id=s["media"]["lite"], file=os.path.relpath(final, self.vdir),
                     fallback="lite", note="veo-fast still %d/5 after %d tries: kept the passing veo-lite clip" % (score, s["tries"][stage]))
        else:
            if os.path.exists(final):
                os.replace(final, final[:-4] + ".rejected.mp4")
            s.update(stage="done", status="done", fallback="still",
                     note="Veo could not animate this shot (%d/5 after %d tries): the render uses the still image" % (score, s["tries"][stage]))
        print("%s: %s" % (sid, s["note"]), flush=True)
        self.events.append((sid, "hết lượt thử: " + ("dùng bản veo-lite" if s.get("fallback") == "lite" else "dùng ảnh tĩnh")))

    def next_stage(self, sid, stage):
        """Ambient shots (gentle first-frame motion) keep an accepted veo-lite clip as the final clip and go
        straight to the 1080p upscale (owner, 2026-10-28: saves the veo-fast credits); active shots go lite -> fast."""
        if stage == "lite" and self.shots.get(sid, {}).get("motion_mode", "ambient") != "active":
            lite, final = self.paths(sid)["lite"], self.paths(sid)["fast"]
            if os.path.exists(final):
                os.replace(final, final[:-4] + ".old.mp4")
            shutil.copy2(lite, final)
            self.st(sid)["file"] = os.path.relpath(final, self.vdir)
            return "upscale"
        return NEXT[stage]

    def run_shot(self, sid):
        """Move one shot forward until it is done, waits for the owner, waits for its review, or gflow fails.
        Returns gflow's error code."""
        if sid in self.reviewing:
            return 0
        s = self.st(sid)
        for _ in range(12):  # hard cap: a bug must never turn into a loop of Flow calls
            if s["status"] != "todo" or s["stage"] == "done":
                return 0
            if workqueue.pause_requested(self.vdir):  # the step in progress has finished; stop before the next one
                print("paused by the owner after %s %s" % (sid, s["stage"]), flush=True)
                return 0
            stage = s["stage"]
            if stage == "upscale":
                code, err = self.upscale(sid)
                if code:  # an export never spends credits: retry later, and after 3 failures keep the 720p clip
                    s["upscale_fails"] = s.get("upscale_fails", 0) + 1
                    if s["upscale_fails"] >= 3:
                        s.update(stage="done", status="done", note="1080p export failed %d times: kept the 720p clip" % s["upscale_fails"])
                        print("%s: %s" % (sid, s["note"]), flush=True)
                        self.save()
                        continue
                    self.save()
                    return 100  # transient: nothing billed
            elif s.get("needs_review") and os.path.exists(self.paths(sid)[stage]):
                self.review_later(sid, stage)
                return 0
            else:
                code, err = self.generate(sid, stage)
                if not code:
                    self.review_later(sid, stage)  # the next Flow call starts while Gemini judges this clip
                    return 0
            self.save()
            if code:
                print("FAILED %s %s: %s\n%s" % (sid, stage, STOP_CODES.get(code, "gflow exit %s" % code), err[-600:]), flush=True)
                if "may have made and billed" in err or "Submit was already clicked" in err:
                    # never re-submit on our own: a second run would bill the same clip again
                    s.update(status="ask", note="Flow có thể đã tạo và trừ credit clip %s nhưng gflow không nhận được. "
                             "Mở project Flow kiểm tra; không có thì bấm Làm lại clip (tốn credit lần nữa)." % stage)
                    self.save()
                return code
        s.update(status="ask", note="stopped after 12 steps without finishing: check the log")
        self.save()
        return 98

    def decide(self, sid, approve):
        s = self.st(sid)
        if s["status"] != "ask":
            return "%s is not waiting for a decision (stage %s, %s)" % (sid, s["stage"], s["status"])
        if approve:
            if s["stage"] in self.paths(sid) and not os.path.exists(self.paths(sid)[s["stage"]]):
                return "%s: no %s clip on disk to approve; use redo" % (sid, s["stage"])
            s.update(stage=self.next_stage(sid, s["stage"]), status="todo", note="approved by owner")
        else:  # owner's redo: aim the new prompt at what the reviewer found wrong in the last clip
            rewritten = s.get("history") and self.rewrite_prompt(sid, s["stage"])
            s.update(status="todo", redo_fix=not rewritten,
                     note="redo asked by owner" + ("; Gemini rewrote the prompt" if rewritten else ""))
        self.save()
        return "%s -> %s" % (sid, s["stage"] if approve else "redo " + s["stage"])


def apply_decisions(f):
    """Owner decisions queued by the dashboard (images/runs/flow_decisions.json)."""
    for sid, d in workqueue.take_decisions(f.vdir).items():
        if d == "reset":  # owner remakes a finished clip from veo-lite; the current clip stays until the new one passes
            old = f.st(sid)
            f.state[sid] = {"stage": "lite", "status": "todo", "tries": {}, "history": old.get("history", []),
                            "note": "remade by owner"}
            f.save()
            print("owner decision: %s -> remake from veo-lite" % sid, flush=True)
            continue
        print("owner decision: %s" % f.decide(sid, d == "approve"), flush=True)


def select(f, only, review):
    """Shots ready for their next Flow stage. With review=True, start images Gemini has not scored yet are
    reviewed first (one batch), so nothing waits on a manual review click."""
    def why_not(it):
        sid, shot = it["id"], f.shots.get(it["id"], {})
        s = f.state.get(sid, {"stage": "lite", "status": "todo"})
        if s["stage"] == "done":
            return "done"
        if s["status"] == "ask":
            return "waits for your decision: %s" % s.get("note", "")
        if not (shot.get("veo_prompt") or shot.get("motion")):
            return "no veo_prompt in shots.json"
        if shot.get("end_frame") and not f.end_frame(sid):
            return "end frame %s not made yet" % shot["end_frame"]
        return f.image_block(it) if s["stage"] == "lite" else None

    items = [it for it in f.items if only is None or it["id"] in only]
    unreviewed = [it["id"] for it in items if why_not(it) == "image not reviewed yet"]
    if review and unreviewed:
        print("Gemini reviews %d start image(s) first: %s" % (len(unreviewed), ",".join(unreviewed)), flush=True)
        subprocess.run([sys.executable, "-u", os.path.join(os.path.dirname(HERE), "gemini", "agy_review.py"), f.vdir,
                        "--only", ",".join(unreviewed), "--workers", "3"])
    ready = []
    for it in items:
        why = why_not(it)
        if why:
            print("skip %-6s %s" % (it["id"], why), flush=True)
        else:
            ready.append(it["id"])
    return ready


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--only", help="comma-separated shot ids")
    ap.add_argument("--approve")
    ap.add_argument("--redo")
    ap.add_argument("--skip-review", action="store_true")
    ap.add_argument("--max-redo", type=int, default=5)  # owner, 2026-10-29: retry a 1-2/5 clip up to 5 times
    ap.add_argument("--gap", default="30-75", help="random pause between Flow calls in seconds")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    f = Flow(os.path.abspath(args.video), args)

    if args.approve or args.redo:
        workqueue.add_decision(f.vdir, args.approve or args.redo, bool(args.approve))
    if args.status:
        for sid, s in f.state.items():
            print("%-6s %-8s %-5s %s" % (sid, s["stage"], s["status"], s.get("note", "")))
        return 0
    only = set(args.only.split(",")) if args.only else None
    if not args.dry_run:  # one Flow run per video: a second start leaves its work to the running one
        lock = workqueue.hold(f.vdir, "flow_clips.lock")
        if not lock:
            print("A Flow run for this video is already going; it picks up new approvals and ready shots itself.", flush=True)
            return 0
    if args.dry_run:
        print("%d shot(s) to move forward" % len(select(f, only, review=False)), flush=True)
        return 0
    if not flowcli.available():
        print("gflow not found: uv tool install \"gflow-cli==0.90.0\" --python 3.12", flush=True)
        return 2
    name, link = os.path.basename(f.vdir), notify.video_link(f.vdir)
    tried = {}  # sid -> (stage, status) when this run last left it
    while not workqueue.pause_requested(f.vdir):  # rescan after each pass: new approvals and reviews join the run
        for sid in f.harvest():
            tried.pop(sid, None)  # reviewed: its next step (pass, redo, ask) is new work
        apply_decisions(f)
        todo = [sid for sid in select(f, only, review=True)
                if sid not in f.reviewing and tried.get(sid) != (f.st(sid)["stage"], f.st(sid)["status"])]
        if not todo:
            if f.reviewing:  # nothing for Flow until a review comes back
                for sid in f.harvest(wait=True):
                    tried.pop(sid, None)
                continue
            break
        print("%d shot(s) to move forward (lite test -> fast for active shots -> 1080p)" % len(todo), flush=True)
        for sid in todo:
            if workqueue.pause_requested(f.vdir):
                break
            apply_decisions(f)
            for done in f.harvest():
                tried.pop(done, None)
            code = f.run_shot(sid)
            tried[sid] = (f.st(sid)["stage"], f.st(sid)["status"])
            if not code:
                continue
            st = f.st(sid)
            if st["status"] == "ask" or st.get("unfetched"):
                # this shot is parked safely (waits for the owner, or its paid clip is recorded): go on with the others
                print("%s parked (%s); continuing with the other shots" % (sid, STOP_CODES.get(code, "exit %s" % code)), flush=True)
                continue
            kind = FAIL_KIND.get(code, "hard")
            workqueue.set_auto(f.vdir, last_error={"code": code, "shot": sid, "kind": kind,
                                                   "text": STOP_CODES.get(code, "gflow exit %s" % code), "at": time.strftime("%Y-%m-%d %H:%M:%S")})
            print("Stopped at %s: %s (%s)." % (sid, STOP_CODES.get(code, "gflow exit %s" % code), kind), flush=True)
            f.drain()  # clips already made still get their review
            notify.send("%s: Flow dừng ở clip %s. %s. %s\n%s" % (
                name, sid, STOP_CODES.get(code, "gflow lỗi (exit %s)" % code),
                {"transient": "Không mất credit; tự thử lại sau 3 phút.", "waf": "Google tạm chặn; tự chạy lại sau 35 phút."}.get(
                    kind, "Cần bạn xem rồi bấm Tiếp tục."), link))
            return 1
    f.drain()  # a clip being reviewed finishes its review even on pause (no Flow call, no credits)
    if workqueue.pause_requested(f.vdir):
        print("Paused by the owner: the step in progress finished; press Tiếp tục to go on.", flush=True)
    if tried:
        lessons.learn_in_background(f.vdir)  # clip problems become rules for later Veo prompts (minutes; never blocks)
    todo = sorted(tried)
    asks = [sid for sid, s in f.state.items() if s["status"] == "ask"]
    print("\nDone. Waiting for your decision: %s" % (", ".join(asks) or "none"), flush=True)
    if not f.events:
        return 0  # nothing happened in this run: no message
    done_all = sum(1 for i in f.items if f.state.get(i["id"], {}).get("stage") == "done")
    lines = ["%s · lượt Flow vừa làm:" % name]
    by = {}
    for sid, ev in f.events:
        by.setdefault(sid, []).append(ev)
    lines += ["- %s: %s" % (sid, "; ".join(evs)) for sid, evs in by.items()]
    lines.append("Clip xong: %d/%d" % (done_all, len(f.items)))
    if asks:
        lines.append("Cần bạn duyệt: %s" % ", ".join("%s (%s %s/5)" % (sid, f.state[sid]["stage"], f.state[sid].get("score", "?")) for sid in asks))
    notify.send("\n".join(lines) + "\n" + link)
    return 0


if __name__ == "__main__":
    sys.exit(main())
