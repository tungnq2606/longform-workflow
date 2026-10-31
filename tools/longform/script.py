"""The source-language script: chapters → beats → sentences, each factual sentence linked to fact-bank ids.

  script/script.json          current version {"lang", "version", "approved", "approved_at", "chapters": [...]}
  script/versions/vNNN.json   every earlier version

Sentence colours (spec §4.4): red blocks approval, yellow is the owner's call, green is backed by verified facts,
plain is narration. A beat id (B01…) is the unit later languages align to, so it must stay stable across versions.
"""
import json
import os
import re
import time

from tools.longform import factbank, inbox, progress

NOT_NAMES = {"Bạn"}
BANNED = ("chúng ta", "bạn nhỏ")
USABLE = ("verified", "weak", "conflict")


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


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(path + ".tmp", path)


def save(pdir, data, by):
    """Save a new version; returns its number. Approval survives only when no sentence text or fact list changed."""
    old = load(pdir)
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


def is_factual(sentence):
    if sentence.get("kind") == "fact":
        return True
    text = sentence.get("text", "")
    if re.search(r"\d", text):
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
    if re.search(r"\d", text) and linked:
        as_checked = [dict(f, status="verified") if f["status"] == "conflict" else f for f in linked]
        if not factbank.supports_number(as_checked, sources):
            red.append("con số cần 1 nguồn hạng A hoặc 2 nguồn hạng B độc lập")
    if any(f.get("legend") for f in linked) and "tương truyền" not in low:
        red.append('dữ kiện truyền thuyết: phải có "tương truyền"')
    if "chứng minh" in low and any((f.get("kind") or sources.get(f["source"], {}).get("kind")) == "archaeology" for f in linked):
        red.append('khảo cổ: dùng "cho thấy", không dùng "chứng minh"')
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


def approve(pdir, by):
    data = load(pdir)
    if not data:
        raise ValueError("chưa có kịch bản")
    r = report(pdir)
    if r["red"]:
        raise ValueError("còn %d câu đỏ" % r["red"])
    data.update(approved=True, approved_at=time.strftime("%Y-%m-%dT%H:%M:%S"), approved_by=by)
    _write(_path(pdir, "script.json"), data)
    progress.set_step(pdir, "script", "done")
    inbox.resolve_key("script:%s" % os.path.basename(os.path.normpath(pdir)))
    return data
