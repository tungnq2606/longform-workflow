"""Long-form projects: one folder per video, one sub-folder per output language.

  python -m tools.longform.project new 1 "Bạch Đằng 1288" --title "..." --lang vi,en,ja
  python -m tools.longform.project list
"""
import argparse
import datetime as dt
import fcntl
import glob
import json
import os
import re
import tempfile
import threading
import unicodedata
from contextlib import contextmanager

from tools.longform import paths
from tools.longform.languages import load_languages

SOURCE_LANG = "vi"
SHARED_DIRS = ("research", "script", "images/raw", "scenes", "audio")
LANG_DIRS = ("script", "audio", "render", "upload")


def ascii_slug(text):
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def create_project(num, slug, title, langs):
    known = load_languages()
    unknown = [c for c in langs if c not in known]
    if unknown:
        raise ValueError("unknown language code(s): %s (known: %s)" % (", ".join(unknown), ", ".join(known)))
    if glob.glob(os.path.join(paths.projects(), "%03d-*" % num)):
        raise FileExistsError("project number %03d already exists" % num)
    order = [SOURCE_LANG] + [c for c in langs if c != SOURCE_LANG]
    pid = "%03d-%s" % (num, ascii_slug(slug))
    d = os.path.join(paths.projects(), pid)
    for sub in SHARED_DIRS:
        os.makedirs(os.path.join(d, sub))
    for c in order:
        for sub in LANG_DIRS:
            os.makedirs(os.path.join(d, "lang", c, sub))
    meta = {"id": pid, "num": num, "slug": ascii_slug(slug), "title": title, "source_lang": SOURCE_LANG,
            "languages": order, "created": dt.date.today().isoformat()}
    with open(os.path.join(d, "project.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    return d


_new_lock = threading.Lock()


def next_number():
    nums = [int(os.path.basename(d)[:3]) for d in glob.glob(os.path.join(paths.projects(), "[0-9][0-9][0-9]-*"))]
    return max(nums, default=0) + 1


def new_project(title, langs):
    """Studio's "Video mới": slug from the title, next free number."""
    slug = ascii_slug(title)
    if not slug:
        raise ValueError("tên không có chữ Latin, không tạo được tên thư mục")
    with _new_lock:
        for _ in range(5):
            try:
                return create_project(next_number(), slug, title, langs)
            except FileExistsError:
                continue
    raise FileExistsError("không tìm được số dự án trống")


def load_project(pdir):
    with open(os.path.join(pdir, "project.json"), encoding="utf-8") as f:
        return json.load(f)


@contextmanager
def locked(pdir):
    """Cross-process lock of project.json (Studio, job workers and CLI tools all write it)."""
    with open(os.path.join(pdir, ".project.lock"), "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def write_meta(pdir, meta):
    """Atomic write through a temp file of its own (never a shared name), then os.replace. Call it under locked()."""
    fd, tmp = tempfile.mkstemp(prefix=".project.", suffix=".tmp", dir=pdir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=1)
        os.replace(tmp, os.path.join(pdir, "project.json"))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def update_meta(pdir, fn):
    """Locked read-modify-write of project.json: fn(meta) changes meta in place. Returns the saved meta."""
    with locked(pdir):
        meta = load_project(pdir)
        fn(meta)
        write_meta(pdir, meta)
    return meta


def add_language(pdir, code):
    """Add a configured output language to a project and create its folders (Plan 6). Returns the new list."""
    if not isinstance(code, str) or code not in load_languages():
        raise ValueError("ngôn ngữ chưa khai báo trong config/languages.json: %s" % code)
    def add(meta):
        if code in meta["languages"]:
            raise ValueError("dự án đã có ngôn ngữ %s" % code)
        for sub in LANG_DIRS:
            os.makedirs(os.path.join(pdir, "lang", code, sub), exist_ok=True)
        meta["languages"].append(code)
    return update_meta(pdir, add)["languages"]


def list_projects():
    """Every project whose project.json reads; a broken one is skipped so it cannot hide the others."""
    out = []
    for p in sorted(glob.glob(os.path.join(paths.projects(), "*", "project.json"))):
        try:
            out.append(load_project(os.path.dirname(p)))
        except (OSError, ValueError):
            continue
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("num", type=int)
    n.add_argument("slug")
    n.add_argument("--title", default="")
    n.add_argument("--lang", default=SOURCE_LANG)
    sub.add_parser("list")
    a = ap.parse_args()
    if a.cmd == "new":
        print(create_project(a.num, a.slug, a.title or a.slug, [c.strip() for c in a.lang.split(",") if c.strip()]))
    else:
        for p in list_projects():
            print("%s  %s  [%s]" % (p["id"], p["title"], ", ".join(p["languages"])))


if __name__ == "__main__":
    main()
