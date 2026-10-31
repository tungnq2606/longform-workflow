"""The source-language script: chapters → beats → sentences, each factual sentence linked to fact-bank ids.

  script/script.json          current version {"lang", "version", "approved", "approved_at", "chapters": [...]}
  script/versions/vNNN.json   every earlier version

Sentence colours (spec §4.4): red blocks approval, yellow is the owner's call, green is backed by verified facts,
plain is narration. A beat id (B01…) is the unit later languages align to, so it must stay stable across versions.
"""
import fcntl
import json
import os
import re
import time
from contextlib import contextmanager

from tools.longform import factbank, inbox, jobs, progress

NOT_NAMES = {"Bạn"}
BANNED = ("chúng ta", "bạn nhỏ")
USABLE = ("verified", "weak", "conflict")
NUM_WORDS = re.compile(r"\b(mười|mươi|trăm|nghìn|ngàn|vạn|triệu|tỷ|tỉ)\b", re.IGNORECASE)
DIGITS = re.compile(r"\d(?:[\d.,]*\d)?")


def _path(pdir, *parts):
    return os.path.join(pdir, "script", *parts)


def load(pdir):
    try:
        with open(_path(pdir, "script.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def sentences(data):
    for ch in data.get("chapters", []):
        for beat in ch.get("beats", []):
            for s in beat.get("sentences", []):
                yield beat["id"], s


def _content(data):
    return [(s["id"], s["text"], list(s.get("facts", []))) for _, s in sentences(data)] if data else None


@contextmanager
def _locked(pdir):
    os.makedirs(_path(pdir), exist_ok=True)
    with open(_path(pdir, ".lock"), "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(path + ".tmp", path)


def _save(pdir, data, by, base=None):
    old = load(pdir)
    if base is not None and (old or {}).get("version", 0) != base:
        raise ValueError("kịch bản đã đổi (v%d) từ khi bản này bắt đầu (v%d)" % ((old or {}).get("version", 0), base))
    version = (old or {}).get("version", 0) + 1
    if old:
        _write(_path(pdir, "versions", "v%03d.json" % old["version"]), old)
    keep = bool(old and old.get("approved") and _content(old) == _content(data))
    data = dict(data, version=version, approved=keep, approved_at=old.get("approved_at") if keep else None,
                updated_by=by, updated_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
    data.setdefault("lang", "vi")
    _write(_path(pdir, "script.json"), data)
    if not keep:
        progress.set_step(pdir, "script", "doing")
    return version


def save(pdir, data, by, base=None):
    """Save a new version; returns its number. Approval survives only when no sentence text or fact list changed.
    base: the version this edit started from; a newer script on disk refuses the save (ValueError)."""
    with _locked(pdir):
        return _save(pdir, data, by, base)


def update(pdir, fn, by, base=None):
    """Locked read-modify-write: fn(current script) -> new script. Returns the new version."""
    with _locked(pdir):
        return _save(pdir, fn(load(pdir)), by, base)


def is_factual(sentence):
    if sentence.get("kind") == "fact":
        return True
    text = sentence.get("text", "")
    if re.search(r"\d", text) or NUM_WORDS.search(text):
        return True
    start = True
    for tok in re.findall(r"\w+|[:.!?]", text):
        if tok in ":.!?":
            start = True
            continue
        if not start and tok[0].isupper() and tok not in NOT_NAMES:
            return True
        start = False
    return False


def colour(sentence, sources, facts):
    text = sentence.get("text", "")
    low = text.lower()
    red, yellow = [], []
    for w in BANNED:
        if w in low:
            red.append('không dùng "%s"' % w)
    linked = []
    for fid in sentence.get("facts", []):
        f = facts.get(fid)
        if f is None:
            red.append("dữ kiện %s không có trong ngân hàng" % fid)
        elif f["status"] == "rejected":
            red.append("dữ kiện %s đã bị loại" % fid)
        elif f["status"] == "pending":
            red.append("dữ kiện %s chưa kiểm xong" % fid)
        else:
            linked.append(f)
    factual = is_factual(sentence) or bool(sentence.get("facts"))
    if factual and not linked and not any("dữ kiện" in r for r in red):
        red.append("câu nêu sự kiện nhưng chưa gắn dữ kiện đã kiểm")
    has_digits, has_words = bool(re.search(r"\d", text)), bool(NUM_WORDS.search(text))
    if (has_digits or has_words) and linked:
        as_checked = [dict(f, status="verified") if f["status"] == "conflict" else f for f in linked]
        if not factbank.supports_number(as_checked, sources):
            red.append("con số cần 1 nguồn hạng A hoặc 2 nguồn hạng B độc lập")
        known = {re.sub(r"[.,]", "", n) for f in linked for n in DIGITS.findall(f.get("claim", "") + " " + f.get("quote", ""))}
        missing = [n for n in DIGITS.findall(text) if re.sub(r"[.,]", "", n) not in known]
        if missing:
            red.append("số %s không có trong dữ kiện đã gắn" % ", ".join(missing))
        if has_words:
            yellow.append("số viết bằng chữ: bạn tự đối chiếu với dữ kiện")
    if any(f.get("legend") for f in linked) and "tương truyền" not in low:
        red.append('dữ kiện truyền thuyết: phải có "tương truyền"')
    if "chứng minh" in low and any((f.get("kind") or sources.get(f["source"], {}).get("kind")) == "archaeology" for f in linked):
        red.append('khảo cổ: dùng "cho thấy", không dùng "chứng minh"')
    if sentence.get("reviewed") is False:
        yellow.append("agy viết, Claude chưa soát câu này")
    for f in linked:
        if f["status"] == "weak":
            yellow.append("dữ kiện %s chỉ có nguồn yếu" % f["id"])
        elif f["status"] == "conflict":
            yellow.append("dữ kiện %s: các ghi chép vênh nhau" % f["id"])
    if red:
        return {"colour": "red", "reasons": red}
    if yellow:
        return {"colour": "yellow", "reasons": yellow}
    return {"colour": "green" if factual else "plain", "reasons": []}


def report(pdir):
    data = load(pdir)
    sources, facts = factbank.load(pdir)
    rows = []
    for beat, s in sentences(data or {}):
        c = colour(s, sources, facts)
        rows.append({"id": s["id"], "beat": beat, "colour": c["colour"], "reasons": c["reasons"]})
    count = lambda k: sum(r["colour"] == k for r in rows)
    return {"sentences": rows, "red": count("red"), "yellow": count("yellow"), "green": count("green")}


def _pid(pdir):
    return os.path.basename(os.path.normpath(pdir))


def approve(pdir, by):
    pid = _pid(pdir)
    if any(j["kind"] == "claude_review" and j["project"] == pid and j["status"] in ("queued", "running") for j in jobs.list_jobs(500)):
        raise ValueError("Claude đang soát kịch bản, chờ soát xong rồi chốt")
    with _locked(pdir):
        data = load(pdir)
        if not data:
            raise ValueError("chưa có kịch bản")
        r = report(pdir)
        if r["red"]:
            raise ValueError("còn %d câu đỏ" % r["red"])
        data.update(approved=True, approved_at=time.strftime("%Y-%m-%dT%H:%M:%S"), approved_by=by)
        _write(_path(pdir, "script.json"), data)
    progress.set_step(pdir, "script", "done")
    inbox.resolve_key("script:%s" % pid)
    return data


def recheck_approval(pdir):
    """After facts change: an approved script that now has red sentences loses its approval. True when cleared."""
    with _locked(pdir):
        data = load(pdir)
        if not data or not data.get("approved"):
            return False
        r = report(pdir)
        if not r["red"]:
            return False
        data.update(approved=False, approved_at=None)
        _write(_path(pdir, "script.json"), data)
    progress.set_step(pdir, "script", "wait")
    inbox.add(_pid(pdir), "script_approve", "Kịch bản v%d hết được chốt: dữ kiện đổi, giờ có %d câu đỏ" % (data["version"], r["red"]),
              screen="script", key="script:%s" % _pid(pdir))
    return True
