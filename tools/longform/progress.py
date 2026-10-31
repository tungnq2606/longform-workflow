"""Step bar and language strip of a project, stored in project.json ("steps", "lang_status").

Later plans' tools call set_step / set_lang when their step moves; Studio only reads.
States: todo, doing, wait (waiting for the owner), done.
"""
import json
import os

STEPS = [("topic", "Đề tài"), ("script", "Kịch bản"), ("images", "Hình ảnh"), ("scenes", "Cảnh"), ("langs", "Ngôn ngữ"),
         ("render", "Render"), ("upload", "Upload")]
LANG_PARTS = [("script", "kịch bản"), ("voice", "giọng"), ("render", "render")]
STATES = ("todo", "doing", "wait", "done")


def _load(pdir):
    with open(os.path.join(pdir, "project.json"), encoding="utf-8") as f:
        return json.load(f)


def _save(pdir, meta):
    p = os.path.join(pdir, "project.json")
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    os.replace(p + ".tmp", p)


def get(pdir):
    meta = _load(pdir)
    st, ls = meta.get("steps", {}), meta.get("lang_status", {})
    steps = [{"id": i, "label": label, "state": st.get(i, "todo")} for i, label in STEPS]
    langs = [{"code": c, "parts": {p: ls.get(c, {}).get(p, "todo") for p, _ in LANG_PARTS}} for c in meta["languages"]]
    return {"steps": steps, "langs": langs, "done": sum(s["state"] == "done" for s in steps), "total": len(STEPS)}


def _check_state(state):
    if state not in STATES:
        raise ValueError("trạng thái không hợp lệ: %s" % state)


def set_step(pdir, step_id, state):
    if step_id not in dict(STEPS):
        raise ValueError("không có bước %s" % step_id)
    _check_state(state)
    meta = _load(pdir)
    meta.setdefault("steps", {})[step_id] = state
    _save(pdir, meta)


def set_lang(pdir, code, part, state):
    meta = _load(pdir)
    if code not in meta["languages"]:
        raise ValueError("dự án không có ngôn ngữ %s" % code)
    if part not in dict(LANG_PARTS):
        raise ValueError("không có phần %s" % part)
    _check_state(state)
    meta.setdefault("lang_status", {}).setdefault(code, {})[part] = state
    _save(pdir, meta)
