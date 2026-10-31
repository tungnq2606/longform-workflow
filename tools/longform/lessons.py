"""Prompt lessons: what image reviews keep rejecting becomes a MUST rule in later prompts.

library/lessons/prompt_lessons.json = {"updated", "lessons": [{"id", "target": "image"|"clip", "when": [keywords],
"rule", "count", "examples": ["<project>/<item>"], "added"}]}

  rules_for(text)          rules whose keywords occur in the text (or that have none), most frequent first, at most 8
  add(problems, example)   each review problem becomes a lesson; the same rule again only raises its count

No AI merge here (the Shorts-era Gemini merge is archived); a lesson added from a review has no keywords, so it
applies to every image prompt until the owner narrows it.
"""
import fcntl
import hashlib
import json
import os
import re
import time
from contextlib import contextmanager

from tools.longform import paths

MAX_RULES = 8


def path():
    return os.path.join(paths.library(), "lessons", "prompt_lessons.json")


def _load():
    try:
        with open(path(), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {"lessons": []}
    return data if isinstance(data, dict) and isinstance(data.get("lessons"), list) else {"lessons": []}


@contextmanager
def _locked():
    os.makedirs(os.path.dirname(path()), exist_ok=True)
    with open(path() + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def rules_for(text, target="image", limit=MAX_RULES):
    low = (text or "").lower()
    hits = [l for l in _load()["lessons"] if l.get("target", "image") == target
            and (not l.get("when") or any(k.lower() in low for k in l["when"]))]
    hits.sort(key=lambda l: -l.get("count", 1))
    return [l["rule"] for l in hits[:limit]]


def _norm(rule):
    return " ".join(re.sub(r"[^\w\s]", " ", rule.lower()).split())


def add(problems, example):
    with _locked():
        data = _load()
        by_norm = {_norm(l.get("rule", "")): l for l in data["lessons"]}
        changed = False
        for p in problems or []:
            rule = " ".join(str(p).split())
            key = _norm(rule)
            if not key:
                continue
            l = by_norm.get(key)
            if l:
                l["count"] = l.get("count", 1) + 1
                if example not in l.setdefault("examples", []):
                    l["examples"].append(example)
            else:
                l = {"id": "review-" + hashlib.sha1(key.encode()).hexdigest()[:8], "target": "image", "when": [],
                     "rule": rule, "count": 1, "examples": [example], "added": time.strftime("%Y-%m-%d")}
                data["lessons"].append(l)
                by_norm[key] = l
            changed = True
        if not changed:
            return
        data["updated"] = time.strftime("%Y-%m-%d")
        with open(path() + ".tmp", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(path() + ".tmp", path())
