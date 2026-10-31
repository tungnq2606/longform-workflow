"""The four script-step AI jobs. agy writes (research, draft); Claude checks (verify, review). Never the same model
writing and checking, and agy is always run as agy itself, never through Claude (owner, 2026-10-31).

Each job works in its own run folder projects/<id>/research/runs/<kind>-<n>/ (its cwd), gets a task file there, and
writes one result file. on_end imports that file; anything malformed is refused whole with a "Cần bạn" item, so the
fact bank and the script never take half a result.
"""
import json
import os
import re
import shutil
import string

from tools.longform import (agy, claude_box, factbank, images, imgspec, inbox, jobs, library_index, paths, progress,
                            project, script, stylebook)

CLAUDE = "claude"
PROMPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")
USABLE = ("verified", "weak", "conflict")
VERIFY_BATCH = 15
MAX_REQUEST = 4000
KINDS = ("fact", "narration", "question", "joke")


def _project(params):
    pid = claude_box.check_project(params.get("project"))
    if pid is None:
        raise ValueError("thiếu dự án")
    return pid, os.path.join(paths.projects(), pid)


def _request(params):
    r = params.get("request")
    if not isinstance(r, str) or not r.strip() or len(r) > MAX_REQUEST or "\x00" in r:
        raise ValueError("yêu cầu trống hoặc quá dài")
    return r.strip()


def _new_run(pdir, kind):
    base = os.path.join(pdir, "research", "runs")
    os.makedirs(base, exist_ok=True)
    n = 1 + max([int(d.rsplit("-", 1)[1]) for d in os.listdir(base) if d.startswith(kind + "-") and d.rsplit("-", 1)[1].isdigit()],
                default=0)
    run = os.path.join(base, "%s-%d" % (kind, n))
    os.makedirs(os.path.join(run, "pages"))
    return run


def _task(run, name, template, pdir, **values):
    with open(os.path.join(PROMPTS, template), encoding="utf-8") as f:
        text = string.Template(f.read()).safe_substitute(title=project.load_project(pdir)["title"], project_dir=pdir, **values)
    with open(os.path.join(run, name), "w", encoding="utf-8") as f:
        f.write(text)


def _json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def _fact_rows(pdir, ids=None, statuses=None, run=None):
    """Facts for a worker. With `run`, each fact's page (or uploaded file) is copied into run/pages/ and referenced
    relative to the run folder, so a Claude worker never needs access outside its own folder."""
    sources, facts = factbank.load(pdir)
    rows = []
    for f in facts.values():
        if (ids is None or f["id"] in ids) and (statuses is None or f["status"] in statuses):
            src = sources.get(f["source"], {})
            page = f.get("page_file") or src.get("page_file") or ""
            if run and page and os.path.isfile(os.path.join(pdir, page)):
                local = os.path.join("pages", os.path.basename(page))
                shutil.copyfile(os.path.join(pdir, page), os.path.join(run, local))
                page = local
            rows.append({"id": f["id"], "claim": f["claim"], "quote": f["quote"], "quote_lang": f.get("quote_lang", ""),
                         "status": f["status"], "grade": f.get("grade"), "legend": f.get("legend", False),
                         "conflicts_with": f.get("conflicts_with", []), "reports": f.get("reports", ""),
                         "page_by": f.get("page_by", ""), "quote_ok": f.get("quote_ok"),
                         "source": {"title": src.get("title", ""), "url": src.get("url", ""), "kind": src.get("kind", "")},
                         "page_file": page})
    return rows


def _style(run, lang="vi"):
    with open(os.path.join(run, "style.md"), "w", encoding="utf-8") as f:
        f.write("# Quy tắc văn phong (%s)\n\n" % lang + "".join("- %s\n" % r for r in stylebook.kept(lang)))


def _claude_argv(task_file, web=False):
    """Claude works only inside its run folder (its cwd); everything it needs is copied there. No --add-dir, so it
    cannot rewrite the fact bank or the script behind the import checks."""
    cfg = claude_box.config()
    return [CLAUDE, "-p", "Read %s in the current folder and do exactly what it says." % task_file,
            "--output-format", "stream-json", "--verbose", "--permission-mode", cfg["permission_mode"],
            "--allowedTools", "Read", "Write", "Glob", "Grep"] + (["WebFetch"] if web else [])


def _cwd(job):
    return job["params"]["run"]


def _refuse(job, why, screen="script"):
    inbox.add(job["project"], "job_failed", "Kết quả của %s không dùng được: %s" % (job["kind"], why),
              screen=screen, key="job:%s" % job["id"])


def _result(job, name="result.json", screen="script"):
    """The parsed result file, or None after filing why it cannot be used."""
    path = os.path.join(job["params"]["run"], name)
    if not os.path.isfile(path):
        blocked = agy.denied(jobs.read_log(job["id"])[0])
        _refuse(job, ("agy bị chặn quyền: %s" % ", ".join(blocked)) if blocked else "không có file %s" % name, screen)
        return None
    if name.endswith(".jsonl"):
        return path
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except ValueError as e:
        _refuse(job, "%s không phải JSON (%s)" % (name, e), screen)
        return None


def validate_script(data, allowed, reviewed=False):
    """A clean copy of a script result, or ValueError. `allowed` = fact ids a sentence may use; `reviewed` marks
    whether Claude has checked these sentences (agy text stays yellow until it has)."""
    if not isinstance(data, dict) or not isinstance(data.get("chapters"), list) or not data["chapters"]:
        raise ValueError("thiếu chapters")
    beats, sids, chapters = set(), set(), []
    for ch in data["chapters"]:
        if not isinstance(ch, dict) or not isinstance(ch.get("beats"), list):
            raise ValueError("chương hỏng")
        out_beats = []
        for b in ch["beats"]:
            if not isinstance(b, dict) or not isinstance(b.get("id"), str) or not re.fullmatch(r"B\d+", b["id"]) or b["id"] in beats:
                raise ValueError("mã cảnh hỏng hoặc trùng: %s" % (b.get("id") if isinstance(b, dict) else b))
            beats.add(b["id"])
            out_s = []
            for s in b.get("sentences") or []:
                if not isinstance(s, dict) or not isinstance(s.get("id"), str) or not re.fullmatch(r"s\d+", s["id"]) or s["id"] in sids:
                    raise ValueError("mã câu hỏng hoặc trùng: %s" % (s.get("id") if isinstance(s, dict) else s))
                if not isinstance(s.get("text"), str) or not s["text"].strip():
                    raise ValueError("câu %s trống" % s["id"])
                fids = s.get("facts") or []
                if not isinstance(fids, list) or not all(isinstance(f, str) for f in fids):
                    raise ValueError("câu %s: facts phải là danh sách mã" % s["id"])
                bad = [f for f in fids if f not in allowed]
                if bad:
                    raise ValueError("câu %s dùng dữ kiện không được phép: %s" % (s["id"], ", ".join(bad)))
                sids.add(s["id"])
                out_s.append({"id": s["id"], "text": s["text"].strip(), "facts": list(fids), "reviewed": reviewed,
                              "kind": s.get("kind") if s.get("kind") in KINDS else "narration", "note": str(s.get("note") or "")})
            out_beats.append({"id": b["id"], "goal": str(b.get("goal") or ""), "sentences": out_s})
        chapters.append({"id": str(ch.get("id") or "C%02d" % (len(chapters) + 1)), "title": str(ch.get("title") or ""),
                         "beats": out_beats})
    return {"lang": data.get("lang") or "vi", "chapters": chapters}


def _usable_ids(pdir):
    return {f["id"] for f in factbank.load(pdir)[1].values() if f["status"] in USABLE}


def _guarded(fn):
    """Any crash while importing a result becomes a "Cần bạn" item instead of a silent line in the job log."""
    def run(job):
        try:
            fn(job)
        except Exception as e:  # noqa: BLE001
            _refuse(job, "lỗi khi nhập kết quả: %s" % e)
    return run


# ---------------------------------------------------------------- agy_research
def research_build(params):
    pid, pdir = _project(params)
    request = _request(params)
    run = _new_run(pdir, "agy_research")
    _task(run, "TASK.md", "research.md", pdir, request=request)
    params["run"] = run
    return agy.argv("Read TASK.md in the current folder and do exactly what it says. " + agy.NO_TOOLS)


def queue_verify(pid, ids):
    for i in range(0, len(ids), VERIFY_BATCH):
        batch = ids[i:i + VERIFY_BATCH]
        jobs.enqueue("claude_verify", {"project": pid, "facts": batch}, pid, "Claude kiểm %d dữ kiện (%s…)" % (len(batch), batch[0]))


def research_end(job):
    if job["status"] != "done" or not _result(job, "sources.jsonl"):
        return
    pid, pdir = _project(job["params"])
    origin = os.path.basename(job["params"]["run"])
    try:
        counts = factbank.import_research(pdir, job["params"]["run"], origin)
    except ValueError as e:
        return _refuse(job, str(e))
    pending = [f["id"] for f in factbank.load(pdir)[1].values() if f["origin"] == origin and f["status"] == "pending"]
    inbox.add(pid, "research_done", "Đã tìm %d nguồn mới, %d dữ kiện (loại %d vì trích không khớp trang, trùng %d). Claude đang kiểm."
              % (counts["sources_added"], counts["facts_added"], counts["rejected"], counts["duplicates"]),
              screen="script", notify_owner=False)
    queue_verify(pid, pending)


# ---------------------------------------------------------------- claude_verify
def verify_build(params):
    pid, pdir = _project(params)
    ids = params.get("facts")
    _, facts = factbank.load(pdir)
    if not isinstance(ids, list) or not ids or any(i not in facts for i in ids):
        raise ValueError("danh sách dữ kiện không hợp lệ")
    run = _new_run(pdir, "claude_verify")
    _json_file(os.path.join(run, "facts.json"), _fact_rows(pdir, ids=set(ids), run=run))
    _task(run, "VERIFY.md", "verify.md", pdir)
    params["run"] = run
    return _claude_argv("VERIFY.md", web=True)


def verify_end(job):
    claude_box._answers.pop(job["id"], None)
    if job["status"] != "done":
        return
    data = _result(job)
    if data is None:
        return
    pid, pdir = _project(job["params"])
    asked = set(job["params"]["facts"])
    try:
        if not isinstance(data, list):
            raise ValueError("phải là một danh sách")
        for r in data:
            if not isinstance(r, dict) or r.get("id") not in asked or r.get("status") not in ("verified", "weak", "rejected"):
                raise ValueError("mục không hợp lệ: %s" % json.dumps(r, ensure_ascii=False)[:120])
    except ValueError as e:
        return _refuse(job, str(e))
    _, facts = factbank.load(pdir)
    for r in data:
        status = r["status"]
        if status == "verified" and facts[r["id"]].get("conflicts_with"):
            status = "conflict"
        try:
            factbank.set_status(pdir, r["id"], status, "claude", str(r.get("note") or ""), r.get("grade"))
        except ValueError as e:  # e.g. Claude says verified for a quote Studio could not find in the page
            _refuse(job, str(e))
    script.recheck_approval(pdir)


# ---------------------------------------------------------------- agy_draft
def draft_build(params):
    pid, pdir = _project(params)
    request = _request(params)
    run = _new_run(pdir, "agy_draft")
    _json_file(os.path.join(run, "facts.json"), _fact_rows(pdir, statuses=USABLE))
    _style(run)
    cur = script.load(pdir)
    if cur:
        _json_file(os.path.join(run, "current_script.json"), cur)
    _task(run, "DRAFT.md", "draft.md", pdir, request=request)
    params["run"] = run
    params["base_version"] = (cur or {}).get("version", 0)
    return agy.argv("Read DRAFT.md in the current folder and do exactly what it says. " + agy.NO_TOOLS)


def draft_end(job):
    if job["status"] != "done":
        return
    data = _result(job)
    if data is None:
        return
    pid, pdir = _project(job["params"])
    try:
        clean = validate_script(data, _usable_ids(pdir), reviewed=False)
        v = script.save(pdir, clean, "agy", base=job["params"].get("base_version"))
    except ValueError as e:
        return _refuse(job, str(e))
    jobs.enqueue("claude_review", {"project": pid}, pid, "Claude soát kịch bản v%d" % v)


# ---------------------------------------------------------------- claude_review
def review_build(params):
    pid, pdir = _project(params)
    cur = script.load(pdir)
    if not cur:
        raise ValueError("chưa có kịch bản")
    run = _new_run(pdir, "claude_review")
    _json_file(os.path.join(run, "script.json"), cur)
    _json_file(os.path.join(run, "facts.json"), _fact_rows(pdir, statuses=USABLE, run=run))
    _style(run)
    _task(run, "REVIEW.md", "review.md", pdir)
    params["run"] = run
    params["base_version"] = cur["version"]
    return _claude_argv("REVIEW.md")


def review_end(job):
    claude_box._answers.pop(job["id"], None)
    if job["status"] != "done":
        return
    data = _result(job)
    if data is None:
        return
    pid, pdir = _project(job["params"])
    try:
        clean = validate_script(data, _usable_ids(pdir), reviewed=True)
        notes = data.get("notes") if isinstance(data.get("notes"), list) else []
        clean["review_notes"] = [{"sentence": str(n.get("sentence", "")), "note": str(n.get("note", ""))} for n in notes if isinstance(n, dict)]
        v = script.save(pdir, clean, "claude", base=job["params"].get("base_version"))
    except ValueError as e:
        return _refuse(job, str(e))
    progress.set_step(pdir, "script", "wait")
    r = script.report(pdir)
    inbox.add(pid, "script_approve", "Kịch bản v%d chờ bạn chốt (đỏ %d, vàng %d)" % (v, r["red"], r["yellow"]),
              screen="script", key="script:%s" % pid)


# ---------------------------------------------------------------- agy_shotlist (Plan 4)
def library_listing():
    """Reusable backgrounds and hero kits with their pose keys, for the shot list."""
    kits = []
    for c in library_index.summary()["characters"]:
        try:
            with open(os.path.join(paths.library(), "characters", c["id"], "kit.json"), encoding="utf-8") as f:
                poses = sorted(json.load(f).get("images") or {})
        except (OSError, ValueError):
            continue
        kits.append({"id": c["id"], "name": c["name"], "poses": poses})
    return {"backgrounds": [b["id"] for b in library_index.summary()["backgrounds"]], "kits": kits}


def shotlist_build(params):
    pid, pdir = _project(params)
    cur = script.load(pdir)
    if not cur or not cur.get("approved"):
        raise ValueError("kịch bản chưa chốt: chốt kịch bản trước khi lập danh sách ảnh")
    if images.load(pdir):
        raise ValueError("dự án đã có danh sách ảnh")
    run = _new_run(pdir, "agy_shotlist")
    _json_file(os.path.join(run, "script.json"), cur)
    _json_file(os.path.join(run, "library.json"), library_listing())
    _json_file(os.path.join(run, "style.json"), imgspec.style())
    _task(run, "SHOTLIST.md", "shotlist.md", pdir)
    params["run"] = run
    return agy.argv("Read SHOTLIST.md in the current folder and do exactly what it says. " + agy.NO_TOOLS)


def _shot_problems(pdir, items):
    beats = {b for b, _ in script.sentences(script.load(pdir) or {})}
    kits = {k["id"]: set(k["poses"]) for k in library_listing()["kits"]}
    problems = []
    for n, it in enumerate(items, 1):
        if not isinstance(it, dict):
            problems.append("mục %d hỏng" % n)
            continue
        label = "mục %d (%s %s)" % (n, it.get("type"), it.get("beat"))
        if it.get("beat") not in beats:
            problems.append("%s: không có cảnh %s trong kịch bản" % (label, it.get("beat")))
        if it.get("type") == "pose" and it.get("pose_key") in kits.get(it.get("kit"), set()):
            problems.append("%s: bộ %s đã có tư thế %s" % (label, it.get("kit"), it.get("pose_key")))
        try:
            images._check_new(it.get("type"), it.get("spec"), it.get("kit"), it.get("pose_key"), it.get("reuse"))
        except ValueError as e:
            problems.append("%s: %s" % (label, e))
    return problems


def shotlist_end(job):
    if job["status"] != "done":
        return
    data = _result(job, screen="images")
    if data is None:
        return
    pid, pdir = _project(job["params"])
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        return _refuse(job, "thiếu danh sách items", "images")
    problems = _shot_problems(pdir, items)
    if problems:
        return _refuse(job, "; ".join(problems), "images")
    added = [images.add(pdir, it["type"], it["spec"], beat=it.get("beat"), kit=it.get("kit"), pose_key=it.get("pose_key"),
                        reuse=it.get("reuse")) for it in items]
    for it in added:
        if it["state"] == "queued":
            jobs.enqueue("agy_image", {"project": pid, "item": it["id"]}, pid, "agy vẽ %s" % it["id"])
    progress.set_step(pdir, "images", "doing" if any(i["state"] == "queued" for i in added) else "wait")


jobs.register(jobs.Kind("agy_shotlist", "agy", shotlist_build, cwd=_cwd, on_end=_guarded(shotlist_end)))

# Image kinds (agy_image, agy_image_review) live with their worker; importing it registers them.
from tools.longform import image_worker  # noqa: E402,F401

jobs.register(jobs.Kind("agy_research", "agy", research_build, cwd=_cwd, on_end=_guarded(research_end)))
jobs.register(jobs.Kind("claude_verify", "claude", verify_build, cwd=_cwd, on_line=claude_box.on_line, on_end=_guarded(verify_end)))
jobs.register(jobs.Kind("agy_draft", "agy", draft_build, cwd=_cwd, on_end=_guarded(draft_end)))
jobs.register(jobs.Kind("claude_review", "claude", review_build, cwd=_cwd, on_line=claude_box.on_line, on_end=_guarded(review_end)))

# Plan 5 kinds register themselves on import.
from tools.longform import timing  # noqa: E402,F401
from tools.longform import scenes  # noqa: E402,F401
