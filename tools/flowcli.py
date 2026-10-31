"""Shared helpers for calling gflow-cli (Google Flow, unofficial; pinned 0.90.0, audited 2026-10-28).

Every Flow call in this workspace goes through call(): one call at a time per process, a random pause
between calls (Flow's WAF reacts to cumulative cadence), no update check, and the Chrome window parked
where dashboard/config.json "gflow"."window_position" says (macOS keeps windows on a screen).
"""
import fcntl
import json
import os
import random
import shutil
import subprocess
import threading
import time

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GFLOW = shutil.which("gflow") or os.path.expanduser("~/.local/bin/gflow")
try:
    with open(os.path.join(WS, "dashboard", "config.json"), encoding="utf-8") as _f:
        WINDOW_POS = json.load(_f).get("gflow", {}).get("window_position")
except (OSError, ValueError):
    WINDOW_POS = None
_LOCK = threading.Lock()
LOCK_FILE = os.path.join(WS, "dashboard", "jobs", "gflow.lock")  # holds the time of the last Flow call


def available():
    return os.path.exists(GFLOW)


def env():
    e = dict(os.environ, GFLOW_CLI_UPDATE_CHECK="0")
    if WINDOW_POS is not None:
        e.setdefault("GFLOW_CLI_BROWSER_WINDOW_POSITION", WINDOW_POS)
    return e


def call(args, gap=(20, 45)):
    """Run `gflow <args>` after a random pause since the previous call; returns (proc, json_result, seconds).
    One Flow call at a time on this Mac: a file lock covers every process (image job + clip job together),
    and the pause counts from the last call any of them made."""
    with _LOCK, open(LOCK_FILE, "a+") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        lk.seek(0)
        try:
            last = float(lk.read().strip() or 0)
        except ValueError:
            last = 0.0
        wait = random.uniform(*gap) - (time.time() - last)
        if last and wait > 0:
            print("pause %d s before the next Flow call" % wait, flush=True)
            time.sleep(wait)
        t0 = time.time()
        p = subprocess.run([GFLOW] + list(args), capture_output=True, text=True, env=env())
        lk.seek(0)
        lk.truncate()
        lk.write(str(time.time()))
        lk.flush()
    out = (p.stdout or "").strip()
    try:
        res = json.loads(out[out.index("{"):]) if "{" in out else {}
    except ValueError:
        res = {}
    return p, res, round(time.time() - t0)


def balance():
    """The Flow credit balance (int), or None when it cannot be read. Reading spends nothing; it is still a
    Flow page load, so it goes through call() like every other request."""
    p, res, _ = call(["credits", "list", "--json"], gap=(3, 8))
    total = res.get("total_credits") if p.returncode == 0 else None
    return total if isinstance(total, int) else None
