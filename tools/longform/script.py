"""The source-language script: chapters → beats → sentences, each factual sentence linked to fact-bank ids.

  script/script.json          current version {"lang", "version", "approved", "approved_at", "chapters": [...]}
  script/versions/vNNN.json   every earlier version

Sentence colours (spec §4.4): red blocks approval, yellow is the owner's call, green is backed by verified facts,
plain is narration. A beat id (B01…) is the unit later languages align to, so it must stay stable across versions.

Other languages (Plan 6) use the same API with lang="en" etc.: lang/<code>/script/script.json, same shape and the
same beat ids. Their sentences may use only the facts the source script used in that beat (else red), and approval
needs the approved source script and the same beat ids.
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
SOURCE = "vi"
LEGEND_WORDS = {"en": "legend", "ja": "伝説", "de": "legende", "es": "leyenda"}
PROOF_WORDS = {"en": "prove", "ja": "証明", "de": "beweis", "es": "demostr", "fr": "prouv"}
OUTSIDE_BEAT = "dữ kiện không thuộc cảnh này"


def _src(lang):
    return lang is None or lang == SOURCE


def _path(pdir, *parts, lang=None):
    if _src(lang):
        return os.path.join(pdir, "script", *parts)
    return os.path.join(pdir, "lang", lang, "script", *parts)


def load(pdir, lang=None):
    try:
        with open(_path(pdir, "script.json", lang=lang), encoding="utf-8") as f:
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
def _locked(pdir, lang=None):
    os.makedirs(_path(pdir, lang=lang), exist_ok=True)
    with open(_path(pdir, ".lock", lang=lang), "w") as lk:
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


def _set_progress(pdir, lang, state):
    if _src(lang):
        progress.set_step(pdir, "script", state)
    else:
        progress.set_lang(pdir, lang, "script", state)


def _save(pdir, data, by, base=None, lang=None):
    old = load(pdir, lang)
    if base is not None and (old or {}).get("version", 0) != base:
        raise ValueError("kịch bản đã đổi (v%d) từ khi bản này bắt đầu (v%d)" % ((old or {}).get("version", 0), base))
    version = (old or {}).get("version", 0) + 1
    if old:
        _write(_path(pdir, "versions", "v%03d.json" % old["version"], lang=lang), old)
    keep = bool(old and old.get("approved") and _content(old) == _content(data))
    data = dict(data, version=version, approved=keep, approved_at=old.get("approved_at") if keep else None,
                updated_by=by, updated_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
    if _src(lang):
        data.setdefault("lang", "vi")
    else:
        data["lang"] = lang
    _write(_path(pdir, "script.json", lang=lang), data)
    if not keep:
        _set_progress(pdir, lang, "doing")
    return version


def save(pdir, data, by, base=None, lang=None):
    """Save a new version; returns its number. Approval survives only when no sentence text or fact list changed.
    base: the version this edit started from; a newer script on disk refuses the save (ValueError)."""
    with _locked(pdir, lang):
        return _save(pdir, data, by, base, lang)


def update(pdir, fn, by, base=None, lang=None):
    """Locked read-modify-write: fn(current script) -> new script. Returns the new version."""
    with _locked(pdir, lang):
        return _save(pdir, fn(load(pdir, lang)), by, base, lang)


def is_factual(sentence, lang=None):
    if sentence.get("kind") == "fact":
        return True
    text = sentence.get("text", "")
    if not _src(lang):  # capitals mean nothing for German nouns or Japanese: digits, kind and linked facts decide
        return bool(re.search(r"\d", text))
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


def colour(sentence, sources, facts, lang=None):
    text = sentence.get("text", "")
    low = text.lower()
    red, yellow = [], []
    src = _src(lang)
    for w in BANNED if src else ():
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
    factual = is_factual(sentence, lang) or bool(sentence.get("facts"))
    if factual and not linked and not any("dữ kiện" in r for r in red):
        red.append("câu nêu sự kiện nhưng chưa gắn dữ kiện đã kiểm")
    has_digits, has_words = bool(re.search(r"\d", text)), bool(src and NUM_WORDS.search(text))
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
    legend = "tương truyền" if src else LEGEND_WORDS.get(lang, "tương truyền")
    if any(f.get("legend") for f in linked) and legend not in low:
        red.append('dữ kiện truyền thuyết: phải có "%s"' % legend)
    proof = "chứng minh" if src else PROOF_WORDS.get(lang, "chứng minh")
    if proof in low and any((f.get("kind") or sources.get(f["source"], {}).get("kind")) == "archaeology" for f in linked):
        red.append('khảo cổ: dùng "cho thấy", không dùng "chứng minh"' if src else
                   'khảo cổ: không dùng từ "%s" (chứng minh), dùng từ "cho thấy"' % proof)
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


def beat_facts(data):
    """{beat id: [fact ids its sentences use]}, in order of first use."""
    out = {}
    for ch in (data or {}).get("chapters", []):
        for b in ch.get("beats", []):
            lst = out.setdefault(b["id"], [])
            for s in b.get("sentences", []):
                lst += [f for f in s.get("facts", []) if f not in lst]
    return out


def beat_ids(data):
    return [b["id"] for ch in (data or {}).get("chapters", []) for b in ch.get("beats", [])]


def report(pdir, lang=None):
    data = load(pdir, lang)
    sources, facts = factbank.load(pdir)
    allowed = None if _src(lang) else beat_facts(load(pdir))
    rows = []
    for beat, s in sentences(data or {}):
        c = colour(s, sources, facts, lang)
        if allowed is not None:
            outside = [f for f in s.get("facts", []) if f not in allowed.get(beat, [])]
            if outside:
                c = {"colour": "red", "reasons": ["%s: %s" % (OUTSIDE_BEAT, ", ".join(outside))] +
                     (c["reasons"] if c["colour"] == "red" else [])}
        rows.append({"id": s["id"], "beat": beat, "colour": c["colour"], "reasons": c["reasons"]})
    count = lambda k: sum(r["colour"] == k for r in rows)
    return {"sentences": rows, "red": count("red"), "yellow": count("yellow"), "green": count("green")}


def _pid(pdir):
    return os.path.basename(os.path.normpath(pdir))


def approve_key(pdir, lang=None):
    """Inbox key of "this script waits for the owner's approval"."""
    return "script:%s" % _pid(pdir) if _src(lang) else "langscript:%s:%s" % (_pid(pdir), lang)


def _reviewing(pid, lang):
    kind = "claude_review" if _src(lang) else "claude_review_lang"
    return any(j["kind"] == kind and j["project"] == pid and j["status"] in ("queued", "running") and
               (_src(lang) or j["params"].get("lang") == lang) for j in jobs.list_jobs(500))


def approve(pdir, by, lang=None):
    pid = _pid(pdir)
    if _reviewing(pid, lang):
        raise ValueError("Claude đang soát kịch bản, chờ soát xong rồi chốt")
    with _locked(pdir, lang):
        data = load(pdir, lang)
        if not data:
            raise ValueError("chưa có kịch bản")
        if not _src(lang):
            src = load(pdir)
            if not src or not src.get("approved"):
                raise ValueError("kịch bản gốc chưa chốt")
            if beat_ids(data) != beat_ids(src):
                raise ValueError("các cảnh không khớp kịch bản gốc")
        r = report(pdir, lang)
        if r["red"]:
            raise ValueError("còn %d câu đỏ" % r["red"])
        data.update(approved=True, approved_at=time.strftime("%Y-%m-%dT%H:%M:%S"), approved_by=by)
        _write(_path(pdir, "script.json", lang=lang), data)
    _set_progress(pdir, lang, "done")
    inbox.resolve_key(approve_key(pdir, lang))
    if not _src(lang):  # the owner (or the clean review) decided: the flagged sentences no longer wait
        for s in data.get("flags") or []:
            inbox.resolve_key("langflag:%s:%s:%s" % (pid, lang, s.get("sentence")))
    return data


def recheck_approval(pdir, lang=None):
    """After facts change: an approved script that now has red sentences loses its approval. True when cleared."""
    with _locked(pdir, lang):
        data = load(pdir, lang)
        if not data or not data.get("approved"):
            return False
        r = report(pdir, lang)
        if not r["red"]:
            return False
        data.update(approved=False, approved_at=None)
        _write(_path(pdir, "script.json", lang=lang), data)
    _set_progress(pdir, lang, "wait")
    label = "Kịch bản" if _src(lang) else "Kịch bản %s" % lang.upper()
    inbox.add(_pid(pdir), "script_approve", "%s v%d hết được chốt: dữ kiện đổi, giờ có %d câu đỏ" % (label, data["version"], r["red"]),
              screen="script" if _src(lang) else "langs", key=approve_key(pdir, lang))
    return True
