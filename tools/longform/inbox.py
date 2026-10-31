"""The "🔔 Cần bạn" inbox: everything waiting for the owner, across projects.

  from tools.longform import inbox
  inbox.add("001-bach-dang", "image_review", "BG08 được 3/5, chờ bạn duyệt", screen="images", key="img:BG08")

Stored in <state>/inbox.json. Writes take a cross-process lock, because CLI tools add items while Studio runs.
A new item also goes to Telegram (best effort); an item with the same open `key` is updated, not repeated.
"""
import fcntl
import json
import os
import time
import uuid
from contextlib import contextmanager

from tools import notify
from tools.longform import paths


def _file():
    return os.path.join(paths.state(), "inbox.json")


@contextmanager
def _locked():
    with open(_file() + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def _load():
    try:
        with open(_file(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _save(items):
    tmp = _file() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    os.replace(tmp, _file())


def add(project, kind, text, screen="", key=None, notify_owner=True):
    with _locked():
        items = _load()
        for it in items:
            if key and not it["done"] and it.get("key") == key:
                it["text"] = text
                _save(items)
                return it
        it = {"id": uuid.uuid4().hex, "project": project, "kind": kind, "text": text, "screen": screen, "key": key,
              "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "done": False}
        items.append(it)
        _save(items)
    if notify_owner:
        notify.send("🔔 %s\n%s" % (text, notify.link(project, screen)))
    return it


def open_items(project=None):
    return [it for it in reversed(_load()) if not it["done"] and (project is None or it["project"] == project)]


def _resolve(match):
    with _locked():
        items = _load()
        hit = False
        for it in items:
            if not it["done"] and match(it):
                it["done"] = True
                hit = True
        if hit:
            _save(items)
        return hit


def resolve(item_id):
    return _resolve(lambda it: it["id"] == item_id)


def resolve_key(key):
    return _resolve(lambda it: it.get("key") == key)
