"""Structured image specs (spec §3 prompt standard) and the prompt text rendered from them.

A spec is a dict with every field of FIELDS. `props` may be a string or a list (sizes against the body or an object,
never mm/cm). `must_not` is a list. A background (bg) has `people: "none"`: backgrounds never show people.

  validate(spec, kind) -> [Vietnamese problems]
  render(spec, kind)   -> prompt: style lock, the fields, MUST NOT (item + style negative), MUST (lessons)
"""
import json
import os
import re

from tools.longform import lessons, paths

TYPES = ("bg", "prop", "pose")
FIELDS = ("shot", "angle", "layout", "setting", "people", "props", "light", "must_not")
VAGUE = ("some", "a few", "several", "dramatic", "cinematic", "epic", "beautiful")
STYLE = "longform_v1.json"
POSE_LINE = "Exactly one figure. Full body, feet visible. Plain flat chroma green #00B140 background. Portrait framing."
_VAGUE_RE = [(w, re.compile(r"\b%s\b" % re.escape(w), re.IGNORECASE)) for w in VAGUE]


def style():
    with open(os.path.join(paths.library(), "style", STYLE), encoding="utf-8") as f:
        return json.load(f)


def _text(value):
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    return str(value)


def validate(spec, kind):
    if kind not in TYPES:
        return ["loại ảnh không hợp lệ: %s" % kind]
    if not isinstance(spec, dict):
        return ["spec phải là một object"]
    problems = []
    for f in FIELDS:
        v = spec.get(f)
        if f == "must_not":
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                problems.append("must_not phải là danh sách câu")
            continue
        if v is None or (isinstance(v, (str, list)) and not _text(v).strip()):
            problems.append("thiếu trường %s" % f)
            continue
        if not isinstance(v, (str, list)):
            problems.append("trường %s phải là chữ hoặc danh sách" % f)
            continue
        for word, rx in _VAGUE_RE:
            if rx.search(_text(v)):
                problems.append("trường %s có từ mơ hồ \"%s\": thay bằng mô tả cụ thể" % (f, word))
    if kind == "bg" and isinstance(spec.get("people"), str) and spec["people"].strip().lower() != "none":
        problems.append("nền không được có người: trường people phải là \"none\"")
    return problems


def render(spec, kind):
    st = style()
    lines = [st["character"] if kind == "pose" else st["background"], ""]
    for f in FIELDS[:-1]:
        lines.append("%s: %s" % (f.capitalize(), _text(spec.get(f, ""))))
    if kind == "pose":
        lines += ["", POSE_LINE]
    body = "\n".join(lines)
    lines += ["", "MUST NOT:"] + ["- %s" % x for x in list(spec.get("must_not") or []) + [st["negative"]]]
    rules = lessons.rules_for(body)
    if rules:
        lines += ["", "MUST:"] + ["- %s" % r for r in rules]
    return "\n".join(lines)
