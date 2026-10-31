"""Per-language style book (library/stylebook/<lang>.json): voice rules every script writer and reviewer follows.

Self-learning: when the owner corrects the voice in the chat, the AI proposes a rule; it shows in "Cần bạn" and is
used only after the owner keeps it.
"""
import json
import os
import time

from tools.longform import inbox, paths


def _path(lang):
    return os.path.join(paths.library(), "stylebook", "%s.json" % lang)


def load(lang):
    try:
        with open(_path(lang), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"lang": lang, "rules": [], "examples": []}


def _save(lang, book):
    p = _path(lang)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(book, f, ensure_ascii=False, indent=1)
    os.replace(p + ".tmp", p)


def kept(lang):
    return [r["text"] for r in load(lang)["rules"] if r["status"] == "kept"]


def propose(lang, text, source):
    book = load(lang)
    n = max([int(r["id"][1:]) for r in book["rules"] if r["id"][1:].isdigit()], default=0) + 1
    rule = {"id": "R%02d" % n, "text": text.strip(), "status": "proposed", "from": source, "added": time.strftime("%Y-%m-%d")}
    book["rules"].append(rule)
    _save(lang, book)
    inbox.add(None, "style_rule", "Quy tắc văn phong mới (%s): %s" % (lang.upper(), rule["text"]),
              key="style:%s:%s" % (lang, rule["id"]), notify_owner=False)
    return rule


def decide(lang, rule_id, keep):
    book = load(lang)
    for r in book["rules"]:
        if r["id"] == rule_id:
            r["status"] = "kept" if keep else "dropped"
            _save(lang, book)
            inbox.resolve_key("style:%s:%s" % (lang, rule_id))
            return r
    raise KeyError(rule_id)
