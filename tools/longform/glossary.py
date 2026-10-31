"""Per-language glossary and name readings (library/glossary/<lang>.json), shared by every video.

  {"lang": "ja", "names": [{"vi": "Trần Hưng Đạo", "target": "チャン・フン・ダオ", "reading": "", "checked": false, "note": ""}],
   "terms": [...same shape...]}

Seeded rows are proposals (checked: false), not facts: the Claude language review or the owner confirms them.
The rewrite worker gets the table; lang_check uses check() to flag a name written differently from the table.
"""
import json
import os
import unicodedata

from tools.longform import paths

KINDS = ("names", "terms")


def _path(lang):
    return os.path.join(paths.library(), "glossary", "%s.json" % lang)


def load(lang):
    try:
        with open(_path(lang), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    data["lang"] = lang
    for k in KINDS:
        data.setdefault(k, [])
    return data


def _save(lang, data):
    p = _path(lang)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(p + ".tmp", p)


def _norm(text):
    return unicodedata.normalize("NFC", text or "").casefold()


def add(lang, vi, target, kind="names", reading="", checked=False, note=""):
    """Add or replace the row for `vi` (one row per Vietnamese form)."""
    if kind not in KINDS:
        raise ValueError("loại không hợp lệ: %s" % kind)
    vi, target = (vi or "").strip(), (target or "").strip()
    if not vi or not target:
        raise ValueError("thiếu tên tiếng Việt hoặc tên đích")
    data = load(lang)
    row = {"vi": vi, "target": target, "reading": reading, "checked": bool(checked), "note": note}
    rows = data[kind]
    for i, r in enumerate(rows):
        if _norm(r["vi"]) == _norm(vi):
            rows[i] = row
            break
    else:
        rows.append(row)
    _save(lang, data)
    return row


def confirm(lang, vi):
    data = load(lang)
    for k in KINDS:
        for r in data[k]:
            if _norm(r["vi"]) == _norm(vi):
                r["checked"] = True
                _save(lang, data)
                return r
    raise KeyError(vi)


def expected(lang, vi_texts):
    """(vi, target) for each glossary row whose Vietnamese form occurs in the given texts."""
    hay = _norm("\n".join(vi_texts))
    data = load(lang)
    return [(r["vi"], r["target"]) for k in KINDS for r in data[k] if _norm(r["vi"]) in hay]


def check(lang, vi_texts, target_text):
    """Vietnamese messages, one per expected target form missing from the target text."""
    hay = _norm(target_text)
    return ["tên %s phải viết là \"%s\" (bảng thuật ngữ %s)" % (vi, target, lang)
            for vi, target in expected(lang, vi_texts) if _norm(target) not in hay]
