"""Script chat: the owner's message goes straight to agy, never through Claude (owner, 2026-10-31).

Studio hands agy the script, its colour report, the fact bank and the style rules as files in a run folder. agy
answers with result.json ({"reply", "edits", "research", "draft", "rule"}); Studio checks every edit against the fact
bank and applies all of them or none. History: projects/<id>/script/chat.jsonl.
"""
import json
import os
import re
import time

from tools.longform import agy, factbank, jobs, script, stylebook, workers

MAX_MESSAGE = 8000


def _hist_path(pdir):
    return os.path.join(pdir, "script", "chat.jsonl")


def _append(pdir, role, text):
    os.makedirs(os.path.dirname(_hist_path(pdir)), exist_ok=True)
    with open(_hist_path(pdir), "a", encoding="utf-8") as f:
        f.write(json.dumps({"role": role, "text": text, "at": time.strftime("%H:%M")}, ensure_ascii=False) + "\n")


def history(pdir, n=50):
    try:
        with open(_hist_path(pdir), encoding="utf-8") as f:
            return [json.loads(l) for l in f.read().splitlines() if l.strip()][-n:]
    except OSError:
        return []


def build(params):
    pid, pdir = workers._project(params)
    message = params.get("message")
    if not isinstance(message, str) or not message.strip() or len(message) > MAX_MESSAGE or "\x00" in message:
        raise ValueError("tin nhắn trống hoặc quá dài")
    run = workers._new_run(pdir, "agy_chat")
    lines = ["**%s** (%s): %s" % ({"owner": "Chủ kênh", "agy": "agy"}.get(m["role"], m["role"]), m["at"], m["text"])
             for m in history(pdir, 20)]
    with open(os.path.join(run, "chat_history.md"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(lines) + "\n")
    cur = script.load(pdir)
    workers._json_file(os.path.join(run, "script.json"), cur or {})
    workers._json_file(os.path.join(run, "report.json"), script.report(pdir))
    _, facts = factbank.load(pdir)
    workers._json_file(os.path.join(run, "facts.json"), [{"id": f["id"], "status": f["status"], "claim": f["claim"]} for f in facts.values()])
    workers._style(run)
    workers._task(run, "CHAT.md", "chat.md", pdir, message=message.strip())
    _append(pdir, "owner", message.strip())
    params["run"] = run
    params["base_version"] = (cur or {}).get("version", 0)
    return agy.argv("Read CHAT.md in the current folder and do exactly what it says. " + agy.NO_TOOLS)


def apply_edits(data, edits, allowed, reviewed=False):
    """A new script with all edits applied, or ValueError (then nothing is applied). Sentences agy writes are marked
    reviewed=False (yellow until Claude checks them); the owner's own edits pass reviewed=None."""
    if not isinstance(edits, list):
        raise ValueError("edits phải là danh sách")
    if not data:
        raise ValueError("chưa có kịch bản để sửa")
    data = json.loads(json.dumps(data))
    beats = {b["id"]: b for ch in data["chapters"] for b in ch["beats"]}
    where = {s["id"]: b for b in beats.values() for s in b["sentences"]}
    top = max([int(sid[1:]) for sid in where if sid[1:].isdigit()], default=0)
    for e in edits:
        if not isinstance(e, dict):
            raise ValueError("một chỗ sửa không hợp lệ")
        op, fids = e.get("op"), e.get("facts") or []
        for key in ("id", "beat", "after"):
            if e.get(key) is not None and not isinstance(e[key], str):
                raise ValueError("%s phải là chuỗi" % key)
        if op in ("set", "add"):
            if not isinstance(e.get("text"), str) or not e["text"].strip():
                raise ValueError("câu mới trống")
            if not isinstance(fids, list) or not all(isinstance(f, str) for f in fids):
                raise ValueError("facts phải là danh sách mã")
            bad = [f for f in fids if f not in allowed]
            if bad:
                raise ValueError("dữ kiện không được phép: %s" % ", ".join(bad))
        if op == "set":
            b = where.get(e.get("id"))
            if b is None:
                raise ValueError("không có câu %s" % e.get("id"))
            s = next(s for s in b["sentences"] if s["id"] == e["id"])
            s.update(text=e["text"].strip(), facts=list(fids), reviewed=reviewed)
        elif op == "add":
            b = beats.get(e.get("beat"))
            if b is None:
                raise ValueError("không có cảnh %s" % e.get("beat"))
            top += 1
            new = {"id": "s%03d" % top, "text": e["text"].strip(), "facts": list(fids), "reviewed": reviewed,
                   "kind": "fact" if fids else "narration", "note": ""}
            ids = [s["id"] for s in b["sentences"]]
            at = ids.index(e["after"]) + 1 if e.get("after") in ids else len(ids)
            b["sentences"].insert(at, new)
            where[new["id"]] = b
        elif op == "delete":
            b = where.pop(e.get("id"), None)
            if b is None:
                raise ValueError("không có câu %s" % e.get("id"))
            b["sentences"] = [s for s in b["sentences"] if s["id"] != e["id"]]
        else:
            raise ValueError("thao tác lạ: %s" % op)
    return data


def on_end(job):
    try:
        _on_end(job)
    except Exception as e:  # noqa: BLE001  never a silent failure
        _append(workers._project(job["params"])[1], "system", "Lỗi khi nhận câu trả lời của agy: %s" % e)


def _on_end(job):
    pid, pdir = workers._project(job["params"])
    if job["status"] != "done":
        return _append(pdir, "system", "agy không trả lời được (job %s)." % job["status"])
    path = os.path.join(job["params"]["run"], "result.json")
    try:
        with open(path, encoding="utf-8") as f:
            res = json.load(f)
        if not isinstance(res, dict):
            raise ValueError("result.json phải là object")
    except (OSError, ValueError) as e:
        blocked = agy.denied(jobs.read_log(job["id"])[0])
        why = ("agy bị chặn quyền: %s" % ", ".join(blocked)) if blocked else "kết quả không đọc được (%s)" % e
        return _append(pdir, "system", "Không dùng được câu trả lời của agy: %s" % why)
    _append(pdir, "agy", str(res.get("reply") or "(agy không viết trả lời)"))
    if res.get("edits"):
        allowed = workers._usable_ids(pdir)
        try:
            v = script.update(pdir, lambda cur: apply_edits(cur, res["edits"], allowed), "agy-chat",
                              base=job["params"].get("base_version"))
        except ValueError as e:
            _append(pdir, "system", "Không áp dụng chỗ sửa nào của agy: %s" % e)
        else:
            _append(pdir, "system", "Đã lưu kịch bản v%d." % v)
    for key, kind in (("research", "agy_research"), ("draft", "agy_draft")):
        req = res.get(key)
        if isinstance(req, str) and req.strip():
            jobs.enqueue(kind, {"project": pid, "request": req.strip()[:workers.MAX_REQUEST]}, pid,
                         ("agy tìm tư liệu: " if key == "research" else "agy viết nháp: ") + req.strip()[:60])
    rule = res.get("rule")
    if isinstance(rule, str) and rule.strip():
        stylebook.propose("vi", rule.strip(), "chat %s" % pid)


jobs.register(jobs.Kind("agy_chat", "agy", build, cwd=workers._cwd, on_end=on_end))
