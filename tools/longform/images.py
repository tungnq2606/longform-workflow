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
import shutil
import time
from contextlib import contextmanager

from PIL import Image

from tools.longform import cutout, imgspec, inbox, jobs, kit, paths, progress, project

STATES = ("queued", "generating", "reviewing", "pass", "wait", "approved", "rejected", "failed")
PREFIX = {"bg": "BG", "prop": "P", "pose": "H"}
RUNNING = ("queued", "generating", "reviewing")
FINISHED = ("approved", "rejected")
POSE_KEY = re.compile(r"^[a-z0-9-]+\.[a-z0-9-]+$")
KIT_ID = re.compile(r"^[a-z0-9-]+$")
CUTOUT_VI = {"no transparency": "không tách được nền xanh", "touches edge": "nhân vật chạm mép ảnh",
             "key colour left on figure": "còn màu xanh nền trên người nhân vật"}
DECIDABLE = ("pass", "wait", "failed")  # the owner may approve, redo or reject these
JOB_KINDS = ("agy_image", "agy_image_review")
BG_MUST_NOT = "people, human figures, animals, text, letters"  # owner rule: backgrounds have no people, no text


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
    if type == "bg" and isinstance(spec, dict) and BG_MUST_NOT not in (spec.get("must_not") or []):
        spec = dict(spec, must_not=list(spec.get("must_not") or []) + [BG_MUST_NOT])
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


# ---------------------------------------------------------------- owner actions (Studio grid)
def _key(pdir, item_id):
    return "img:%s:%s" % (os.path.basename(pdir), item_id)


def _cutout_problems(it):
    files = it.get("files") or {}
    if not files.get("cutout") or not os.path.isfile(abspath(files["cutout"])):
        return ["chưa có ảnh đã tách nền"]
    out = []
    for p in cutout.check(abspath(files["cutout"]), source=abspath(files["final"])):
        out.append(next((v for k, v in CUTOUT_VI.items() if p.startswith(k)), p))
    return out


def approve(pdir, item_id):
    it = get(pdir, item_id)
    final = (it.get("files") or {}).get("final")
    if it["state"] == "approved":
        raise ValueError("%s đã duyệt rồi" % item_id)
    if it["state"] not in DECIDABLE or not final or not os.path.isfile(abspath(final)):
        raise ValueError("%s chưa có ảnh để duyệt" % item_id)
    if it["type"] == "pose":
        problems = _cutout_problems(it)
        if problems:
            raise ValueError("Không duyệt được %s: %s" % (item_id, "; ".join(problems)))
        problems = kit.add_image(it["kit"], it["pose_key"], abspath(final))
        if problems:
            raise ValueError("Bộ nhân vật %s báo lỗi: %s" % (it["kit"], "; ".join(problems)))
        try:
            kit.write_ts(kit.TS_OUT)
        except SystemExit as e:
            raise ValueError(str(e))
    it = update(pdir, item_id, state="approved", note="bạn duyệt")
    inbox.resolve_key(_key(pdir, item_id))
    return it


def approve_many(pdir, ids):
    out = {"approved": [], "errors": {}}
    for i in ids:
        try:
            approve(pdir, i)
            out["approved"].append(i)
        except KeyError:
            out["errors"][i] = "không có ảnh %s" % i
        except ValueError as e:
            out["errors"][i] = str(e)
    return out


def busy(pdir, it):
    """True while the item is mid-way and a queued or running image job still holds it (a dead job leaves it free)."""
    return it["state"] in RUNNING and bool(jobs.live(JOB_KINDS, project=os.path.basename(pdir), item=it["id"]))


def redo(pdir, item_id, note):
    """Redraw with the owner's note as the fix. Attempts stay as they are: the owner's redo is not an auto redo."""
    it = get(pdir, item_id)
    if it.get("reuse"):
        raise ValueError("%s là nền dùng lại từ thư viện" % item_id)
    if busy(pdir, it):
        raise ValueError("%s đang được làm" % item_id)
    pid = os.path.basename(pdir)
    it = update(pdir, item_id, state="queued", fix=str(note or "").strip(), note="bạn yêu cầu vẽ lại: %s" % (note or ""))
    jobs.enqueue("agy_image", {"project": pid, "item": item_id}, pid, "agy vẽ lại %s (bạn yêu cầu)" % item_id)
    inbox.resolve_key(_key(pdir, item_id))
    return it


def reject(pdir, item_id):
    it = get(pdir, item_id)
    if it["state"] in ("generating", "reviewing") and busy(pdir, it):
        raise ValueError("%s đang được làm" % item_id)
    it = update(pdir, item_id, state="rejected", note="bạn bỏ")
    inbox.resolve_key(_key(pdir, item_id))
    return it


def save_background(pdir, item_id, name):
    """Copy an approved background into the library, with an empty geometry sidecar (filled in Plan 5)."""
    it = get(pdir, item_id)
    if it["type"] != "bg" or it["state"] != "approved" or it.get("reuse"):
        raise ValueError("chỉ nền đã duyệt (không phải nền dùng lại) mới đưa vào thư viện")
    slug = project.ascii_slug(str(name or ""))
    if not slug:
        raise ValueError("thiếu tên nền")
    d = os.path.join(paths.library(), "backgrounds")
    os.makedirs(d, exist_ok=True)
    if os.path.exists(os.path.join(d, slug + ".png")):
        raise ValueError("thư viện đã có nền %s" % slug)
    shutil.copyfile(abspath(it["files"]["final"]), os.path.join(d, slug + ".png"))
    with open(os.path.join(d, slug + ".json"), "w", encoding="utf-8") as f:
        json.dump({"horizonY": None, "groundY": None, "path": []}, f)
    update(pdir, item_id, library=slug)
    return slug


THUMB_W = 480


def file_of(pdir, item_id, which):
    """Absolute path of one of an item's own files (raw, final, cutout), looked up from the item, never from the
    caller's text. KeyError when the item or that file does not exist."""
    if which not in ("raw", "final", "cutout"):
        raise KeyError(which)
    rel_path = (get(pdir, item_id).get("files") or {}).get(which)
    if not rel_path or not os.path.isfile(abspath(rel_path)):
        raise KeyError(which)
    return abspath(rel_path)


def thumb(pdir, item_id):
    """A small cached preview for the grid: the cutout of a pose (PNG), else the final or raw image (JPEG)."""
    for which in ("cutout", "final", "raw"):
        try:
            src = file_of(pdir, item_id, which)
            break
        except KeyError:
            continue
    else:
        raise KeyError(item_id)
    png = which == "cutout"
    d = os.path.join(pdir, "images", "thumbs")
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, item_id + (".png" if png else ".jpg"))
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
        return out
    with Image.open(src) as im:
        im.thumbnail((THUMB_W, THUMB_W))
        if png:
            im.convert("RGBA").save(out + ".tmp", "PNG")
        else:
            im.convert("RGB").save(out + ".tmp", "JPEG", quality=85)
    os.replace(out + ".tmp", out)
    return out
