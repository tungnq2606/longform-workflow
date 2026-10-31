"""Licensed music and sound effects shared by every video: library/audio/index.json + the files next to it.

  {"music": [{"id", "file": "music/<id>.mp3", "kind": "music", "mood": "opening|tension|battle|ending", "license", "added"}],
   "sfx":   [{"id", "file": "sfx/<id>.wav", "kind": "sfx", "tags": ["sword", ...], "license", "added"}]}

  python -m tools.longform.audio_lib add <file> music|sfx <id> --license "text + URL" [--mood battle] [--tags sword,drum]

Every file needs a licence that allows monetised YouTube (spec §4.8); adding one also writes a line to LICENSES.md.
A missing file or an empty licence shows in problems(); renders never use such an entry.
"""
import argparse
import fcntl
import json
import os
import re
import shutil
import sys
import time
from contextlib import contextmanager

from tools.longform import inbox, paths

KINDS = ("music", "sfx")
MOODS = ("opening", "tension", "battle", "ending")
TAGS = ("sword", "drum", "water", "oar", "march", "hammer", "wind")
EXTS = (".mp3", ".wav")
AUDIO_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,60}$")
EMPTY_KEY = "audio:empty"
LICENSES_HEAD = "\n## Audio library (library/audio/)\n\n| id | kind | file | licence | added |\n|---|---|---|---|---|\n"


def _dir():
    return os.path.join(paths.library(), "audio")


def _index():
    return os.path.join(_dir(), "index.json")


@contextmanager
def _locked():
    os.makedirs(_dir(), exist_ok=True)
    with open(os.path.join(_dir(), ".lock"), "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def load():
    try:
        with open(_index(), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    return {"music": list(data.get("music") or []), "sfx": list(data.get("sfx") or [])}


def entries():
    idx = load()
    return idx["music"] + idx["sfx"]


def ids():
    return {e["id"] for e in entries()}


def get(audio_id):
    for e in entries():
        if e["id"] == audio_id:
            return e
    raise KeyError(audio_id)


def usable(e):
    """An entry a render may use: it has a licence and its file is in the library."""
    return bool(str(e.get("license") or "").strip()) and os.path.isfile(os.path.join(_dir(), e.get("file") or ""))


def _log_license(e):
    p = os.path.join(paths.root(), "LICENSES.md")
    try:
        with open(p, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        text = ""
    line = "| %s | %s | library/audio/%s | %s | %s |\n" % (e["id"], e["kind"], e["file"], e["license"].replace("|", "/"), e["added"])
    with open(p, "a", encoding="utf-8") as f:
        if "## Audio library (library/audio/)" not in text:
            f.write(LICENSES_HEAD)
        f.write(line)


def add(path, kind, id, license, mood=None, tags=()):
    if kind not in KINDS:
        raise ValueError("loại phải là music hoặc sfx")
    if not isinstance(id, str) or not AUDIO_ID.match(id):
        raise ValueError("mã âm thanh chỉ gồm chữ thường, số, gạch ngang: %s" % id)
    license = str(license or "").strip()
    if not license:
        raise ValueError("thiếu giấy phép: chỉ nhận file có giấy phép cho YouTube kiếm tiền")
    ext = os.path.splitext(path)[1].lower()
    if ext not in EXTS:
        raise ValueError("chỉ nhận file mp3 hoặc wav")
    if not os.path.isfile(path):
        raise ValueError("không có file %s" % path)
    if kind == "music" and mood not in MOODS:
        raise ValueError("nhạc cần mood: %s" % ", ".join(MOODS))
    tags = [t for t in (tags or []) if t]
    if kind == "sfx" and (not tags or any(t not in TAGS for t in tags)):
        raise ValueError("hiệu ứng cần tags trong: %s" % ", ".join(TAGS))
    with _locked():
        idx = load()
        if id in {e["id"] for e in idx["music"] + idx["sfx"]}:
            raise ValueError("mã âm thanh trùng: %s" % id)
        rel = "%s/%s%s" % (kind, id, ext)
        os.makedirs(os.path.join(_dir(), kind), exist_ok=True)
        shutil.copyfile(path, os.path.join(_dir(), rel))
        e = {"id": id, "file": rel, "kind": kind, "license": license, "added": time.strftime("%Y-%m-%d")}
        if kind == "music":
            e["mood"] = mood
        else:
            e["tags"] = tags
        idx[kind].append(e)
        with open(_index() + ".tmp", "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False, indent=1)
        os.replace(_index() + ".tmp", _index())
        _log_license(e)
    inbox.resolve_key(EMPTY_KEY)
    return e


def problems():
    out = []
    for e in entries():
        if not str(e.get("license") or "").strip():
            out.append("%s: không có giấy phép" % e["id"])
        if not os.path.isfile(os.path.join(_dir(), e.get("file") or "")):
            out.append("%s: thiếu file %s" % (e["id"], e.get("file")))
    return out


def by_mood(mood):
    return [e for e in load()["music"] if e.get("mood") == mood]


def by_tag(tag):
    return [e for e in load()["sfx"] if tag in (e.get("tags") or [])]


def warn_if_empty(project):
    """One "Cần bạn" item while the library is empty (same key, so never repeated)."""
    if not entries():
        inbox.add(project, "audio_missing", "Thư viện nhạc/hiệu ứng trống: thêm file có giấy phép YouTube kiếm tiền",
                  screen="scenes", key=EMPTY_KEY)
        return True
    return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("file")
    a.add_argument("kind", choices=KINDS)
    a.add_argument("id")
    a.add_argument("--license", required=True)
    a.add_argument("--mood", choices=MOODS)
    a.add_argument("--tags", default="")
    sub.add_parser("check")
    o = ap.parse_args(argv)
    if o.cmd == "add":
        try:
            print(json.dumps(add(o.file, o.kind, o.id, o.license, o.mood, o.tags.split(",")), ensure_ascii=False))
        except ValueError as e:
            sys.exit("lỗi: %s" % e)
    else:
        probs = problems()
        print("\n".join(probs) if probs else "ok")
        sys.exit(1 if probs else 0)


if __name__ == "__main__":
    main()
