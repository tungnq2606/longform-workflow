"""Per-video work queue on disk (images/runs/), shared by the dashboard and the image/clip runners.

Nothing the owner asks for lives only in memory: redo requests and clip decisions are appended to files,
the runners take them under a file lock, and the dashboard's reconciler restarts a runner whenever work is
left over (after a crash, a dashboard restart, or a request that arrived as a run was ending).

  auto.json            {"enabled": bool, "pause": bool, "reason": str, ...}  automation switch per video
  image_queue.json     ["S04A", ...]                     images the owner asked to make again
  flow_decisions.json  {"S03B": "approve" | "redo"}       clip decisions not yet applied
"""
import fcntl
import json
import os
import time


def runs(vdir):
    return os.path.join(os.path.abspath(vdir), "images", "runs")


def _path(vdir, name):
    os.makedirs(runs(vdir), exist_ok=True)
    return os.path.join(runs(vdir), name)


def _update(vdir, name, fn, default):
    """Read-modify-write one queue file under an exclusive lock; returns fn's result."""
    with open(_path(vdir, name + ".lock"), "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        p = _path(vdir, name)
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = default
        data, out = fn(data)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, ensure_ascii=False)
        os.replace(tmp, p)
        return out


def add_images(vdir, ids):
    _update(vdir, "image_queue.json", lambda q: (q + [i for i in ids if i not in q], None), [])


def take_images(vdir):
    return _update(vdir, "image_queue.json", lambda q: ([], q), [])


def add_decision(vdir, sid, approve, value=None):
    """approve=True/False -> "approve"/"redo"; value overrides it (e.g. "reset": remake the clip from veo-lite)."""
    def fn(q):
        q[sid] = value or ("approve" if approve else "redo")
        return q, None
    _update(vdir, "flow_decisions.json", fn, {})


def take_decisions(vdir):
    return _update(vdir, "flow_decisions.json", lambda q: ({}, q), {})


def peek(vdir, name, default):
    try:
        with open(_path(vdir, name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def auto(vdir):
    return peek(vdir, "auto.json", {})


def set_auto(vdir, **kw):
    def fn(a):
        a.update(kw, at=time.strftime("%Y-%m-%d %H:%M:%S"))
        return a, a
    return _update(vdir, "auto.json", fn, {})


def pause_requested(vdir):
    """Runners check this between tasks: the task in progress always finishes."""
    return bool(auto(vdir).get("pause"))


def hold(vdir, name):
    """Take a runner's single-instance lock without waiting; returns the open file or None if busy."""
    f = open(_path(vdir, name), "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return f
    except OSError:
        f.close()
        return None


def busy(vdir, name):
    f = hold(vdir, name)
    if f:
        f.close()
        return False
    return True
