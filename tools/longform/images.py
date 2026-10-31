"""Image items of one project: every background, prop and hero pose the video needs, each with its own state.

  images/items.json   [{"id": "BG01|P01|H01", "type": "bg|prop|pose", "beat", "kit", "pose_key", "spec", "prompt",
                        "refs", "state", "attempts", "files": {"raw", "final", "cutout"}, "score", "problems", "fix",
                        "history": [{"at", "event", "score", "note"}], "reuse"}]

States: queued → generating → reviewing → pass (score 4–5) | wait (the owner decides) → approved | rejected; failed
when a worker crashed. Paths in "refs" and "files" are relative to the workspace root. Several workers update items
at once, so every write holds images/.lock and re-reads the file.
"""
import fcntl
import json
import os
import re
import time
from contextlib import contextmanager

from tools.longform import imgspec, paths, progress

STATES = ("queued", "generating", "reviewing", "pass", "wait", "approved", "rejected", "failed")
PREFIX = {"bg": "BG", "prop": "P", "pose": "H"}
RUNNING = ("queued", "generating", "reviewing")
FINISHED = ("approved", "rejected")
POSE_KEY = re.compile(r"^[a-z0-9-]+\.[a-z0-9-]+$")
KIT_ID = re.compile(r"^[a-z0-9-]+$")


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _file(pdir):
    return os.path.join(pdir, "images", "items.json")


def rel(path):
    return os.path.relpath(path, paths.root())


def abspath(relpath):
    return os.path.join(paths.root(), relpath)


@contextmanager
def _locked(pdir):
    os.makedirs(os.path.join(pdir, "images"), exist_ok=True)
    with open(os.path.join(pdir, "images", ".lock"), "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def load(pdir):
    try:
        with open(_file(pdir), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def get(pdir, item_id):
    for it in load(pdir):
        if it["id"] == item_id:
            return it
    raise KeyError(item_id)


def _save(pdir, items):
    with open(_file(pdir) + ".tmp", "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    os.replace(_file(pdir) + ".tmp", _file(pdir))
    _sync_step(pdir, items)


def _sync_step(pdir, items):
    """doing while anything runs; done when every item is approved or rejected; otherwise the owner has to act
    (a score 3, a pass to approve, a failed worker), so wait."""
    if not items:
        return
    states = [i["state"] for i in items]
    if any(s in RUNNING for s in states):
        step = "doing"
    elif all(s in FINISHED for s in states):
        step = "done"
    else:
        step = "wait"
    progress.set_step(pdir, "images", step)


def counts(pdir):
    out = {}
    for it in load(pdir):
        out[it["state"]] = out.get(it["state"], 0) + 1
    return out


def kit_refs(kit_id):
    """The kit's model sheet and its standing pose: what agy draws a new pose from."""
    d = os.path.join(paths.library(), "characters", kit_id)
    with open(os.path.join(d, "kit.json"), encoding="utf-8") as f:
        k = json.load(f)
    refs = []
    if k.get("model_sheet") and os.path.isfile(os.path.join(d, k["model_sheet"])):
        refs.append(rel(os.path.join(d, k["model_sheet"])))
    imgs = k.get("images") or {}
    stand = next((v for key, v in imgs.items() if key.startswith("stand.")), next(iter(imgs.values()), None))
    if stand and os.path.isfile(os.path.join(d, stand["file"])):
        refs.append(rel(os.path.join(d, stand["file"])))
    return refs


def _check_new(kind, spec, kit, pose_key, reuse):
    if kind not in imgspec.TYPES:
        raise ValueError("loại ảnh không hợp lệ: %s" % kind)
    if reuse is not None:
        if kind != "bg":
            raise ValueError("chỉ nền mới dùng lại từ thư viện")
        if not isinstance(reuse, str) or not KIT_ID.match(reuse) or \
                not os.path.isfile(os.path.join(paths.library(), "backgrounds", reuse + ".png")):
            raise ValueError("thư viện không có nền %s" % reuse)
        return
    problems = imgspec.validate(spec, kind)
    if kind == "pose":
        if not isinstance(kit, str) or not KIT_ID.match(kit) or \
                not os.path.isfile(os.path.join(paths.library(), "characters", kit, "kit.json")):
            problems.append("không có bộ nhân vật %s" % kit)
        if not isinstance(pose_key, str) or not POSE_KEY.match(pose_key):
            problems.append("tên tư thế phải dạng tu-the.bieu-cam (chữ thường), ví dụ point.determined")
    if problems:
        raise ValueError("; ".join(problems))


def add(pdir, type, spec, beat=None, kit=None, pose_key=None, reuse=None):
    _check_new(type, spec, kit, pose_key, reuse)
    with _locked(pdir):
        items = load(pdir)
        prefix = PREFIX[type]
        nums = [int(i["id"][len(prefix):]) for i in items if re.fullmatch(prefix + r"\d+", i["id"])]
        item = {"id": "%s%02d" % (prefix, max(nums, default=0) + 1), "type": type, "beat": beat,
                "kit": kit if type == "pose" else None, "pose_key": pose_key if type == "pose" else None,
                "spec": spec, "prompt": "", "refs": [], "state": "queued", "attempts": 0,
                "files": {"raw": None, "final": None, "cutout": None}, "score": None, "problems": [], "fix": "",
                "history": [], "reuse": reuse}
        if reuse:
            item["state"] = "approved"
            item["files"]["final"] = rel(os.path.join(paths.library(), "backgrounds", reuse + ".png"))
        else:
            item["prompt"] = imgspec.render(spec, type)
            if type == "pose":
                item["refs"] = kit_refs(kit)
        item["history"].append({"at": _now(), "event": item["state"], "score": None,
                                "note": "dùng lại nền %s" % reuse if reuse else ""})
        items.append(item)
        _save(pdir, items)
    return item


def update(pdir, item_id, note="", **fields):
    """Set fields of one item; a state change adds a history event (with `note`)."""
    if "state" in fields and fields["state"] not in STATES:
        raise ValueError("trạng thái ảnh không hợp lệ: %s" % fields["state"])
    with _locked(pdir):
        items = load(pdir)
        for it in items:
            if it["id"] == item_id:
                old = it["state"]
                it.update(fields)
                if "state" in fields and fields["state"] != old:
                    it["history"].append({"at": _now(), "event": it["state"], "score": it.get("score"), "note": note})
                _save(pdir, items)
                return it
    raise KeyError(item_id)
