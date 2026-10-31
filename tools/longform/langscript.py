"""Per-language scripts (Plan 6): agy rewrites the script natively per language, code checks it, Claude reviews it.

No translation (owner, 2026-10-31): the rewrite worker gets each beat's goal, its fact ids with claims and quotes,
the glossary, the language style book and the localization guide, never the Vietnamese sentences. Each beat may use
only the facts the source script used in that beat (script.report marks anything else red).

  agy_rewrite         (agy)    params {"project", "lang"} -> lang/<code>/script/script.json (sentences reviewed=False)
  claude_review_lang  (claude) params {"project", "lang"} -> reviewed script + flags with back-translations

A language whose checks pass and whose review flags nothing is approved automatically (spec §5); every flag goes to
"Cần bạn" with a Vietnamese back-translation for the owner to decide.
"""
import json
import os
import shutil

from tools.longform import (agy, claude_box, glossary, inbox, jobs, languages, paths, progress, project, script,
                            stylebook, workers)

SCREEN = "langs"


def outline(pdir):
    """[{"beat", "goal", "facts": [ids], "chapter"}] from the approved source script (ValueError when not approved)."""
    src = script.load(pdir)
    if not src or not src.get("approved"):
        raise ValueError("kịch bản gốc chưa chốt: chốt kịch bản tiếng Việt trước khi viết ngôn ngữ khác")
    used = script.beat_facts(src)
    return [{"beat": b["id"], "goal": b.get("goal", ""), "facts": used.get(b["id"], []), "chapter": ch["id"]}
            for ch in src["chapters"] for b in ch["beats"]]


def _check_path(pdir, lang):
    return os.path.join(pdir, "lang", lang, "script", "check.json")


def check(pdir, lang):
    """The automatic checks of one language: the colour report (incl. facts outside their beat), glossary misses
    (yellow, on the beat's first sentence) and whole-script problems (beats missing or extra)."""
    data = script.load(pdir, lang)
    src = script.load(pdir)
    rep = script.report(pdir, lang)
    problems, per = [], {}
    if not data:
        return {"report": rep, "problems": ["chưa có kịch bản %s" % lang], "per_sentence": {}, "glossary_misses": 0}
    want, have = script.beat_ids(src), script.beat_ids(data)
    missing, extra = [b for b in want if b not in have], [b for b in have if b not in want]
    if missing:
        problems.append("thiếu cảnh %s" % ", ".join(missing))
    if extra:
        problems.append("thừa cảnh %s" % ", ".join(extra))
    rows = {r["id"]: r for r in rep["sentences"]}
    for r in rep["sentences"]:
        outside = [x for x in r["reasons"] if x.startswith(script.OUTSIDE_BEAT)]
        if outside:
            per.setdefault(r["id"], []).extend(outside)
    src_text = {}
    for beat, s in script.sentences(src or {}):
        src_text.setdefault(beat, []).append(s["text"])
    misses = 0
    for ch in data["chapters"]:
        for b in ch["beats"]:
            if not b["sentences"]:
                continue
            msgs = glossary.check(lang, src_text.get(b["id"], []), "\n".join(s["text"] for s in b["sentences"]))
            if not msgs:
                continue
            misses += len(msgs)
            sid = b["sentences"][0]["id"]
            per.setdefault(sid, []).extend(msgs)
            row = rows[sid]
            row["reasons"] = row["reasons"] + msgs
            if row["colour"] in ("green", "plain"):
                row["colour"] = "yellow"
    count = lambda k: sum(r["colour"] == k for r in rep["sentences"])
    rep.update(red=count("red"), yellow=count("yellow"), green=count("green"))
    return {"report": rep, "problems": problems, "per_sentence": per, "glossary_misses": misses}


def record_check(pdir, lang):
    """The lang_check record: run the checks and keep them in lang/<code>/script/check.json."""
    out = check(pdir, lang)
    p = _check_path(pdir, lang)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    os.replace(p + ".tmp", p)
    return out


def load_check(pdir, lang):
    try:
        with open(_check_path(pdir, lang), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------- shared helpers
def _target(params):
    """(pid, pdir, lang) for a non-source project language, else ValueError."""
    pid, pdir = workers._project(params)
    lang = params.get("lang")
    meta = project.load_project(pdir)
    if not isinstance(lang, str) or lang == meta.get("source_lang", "vi") or lang not in meta["languages"] \
            or lang not in languages.load_languages():
        raise ValueError("ngôn ngữ không hợp lệ cho dự án: %s" % lang)
    return pid, pdir, lang


def _new_run(pdir, kind, lang):
    return workers._new_run(pdir, "%s_%s" % (kind, lang))


def _outline_rows(pdir):
    """Beats with goals and fact claims + quotes. No source sentences."""
    beats = outline(pdir)
    ids = {f for b in beats for f in b["facts"]}
    rows = {r["id"]: {k: r[k] for k in ("id", "claim", "quote", "quote_lang", "status", "legend", "conflicts_with")}
            for r in workers._fact_rows(pdir, ids=ids)}
    return {"beats": [{"beat": b["beat"], "chapter": b["chapter"], "goal": b["goal"],
                       "facts": [rows[f] for f in b["facts"] if f in rows]} for b in beats]}


def _common_files(run, pdir, lang):
    workers._json_file(os.path.join(run, "outline.json"), _outline_rows(pdir))
    workers._json_file(os.path.join(run, "glossary.json"), glossary.load(lang))
    workers._style(run, lang)
    guide = os.path.join(paths.library(), "localization", "GUIDE.md")
    if os.path.isfile(guide):
        shutil.copyfile(guide, os.path.join(run, "GUIDE.md"))


def _task(run, name, template, pdir, lang, **values):
    workers._task(run, name, template, pdir, lang=lang, lang_name=languages.load_languages()[lang].name, **values)


def _refuse(job, why):
    workers._refuse(job, why, SCREEN)


def _guarded(fn):
    def run(job):
        try:
            fn(job)
        except Exception as e:  # noqa: BLE001  a crash while importing becomes a "Cần bạn" item
            _refuse(job, "lỗi khi nhập kết quả: %s" % e)
    return run


def _clean(pdir, data, reviewed):
    """validate_script against the union of beat facts, plus exactly the source beat ids (else ValueError)."""
    beats = outline(pdir)
    allowed = {f for b in beats for f in b["facts"]}
    clean = workers.validate_script(data, allowed, reviewed=reviewed)
    want, have = [b["beat"] for b in beats], script.beat_ids(clean)
    missing, extra = [b for b in want if b not in have], [b for b in have if b not in want]
    if missing or extra:
        raise ValueError("cảnh không khớp kịch bản gốc (thiếu %s; thừa %s)" % (", ".join(missing) or "-", ", ".join(extra) or "-"))
    return clean


# ---------------------------------------------------------------- agy_rewrite
def rewrite_build(params):
    pid, pdir, lang = _target(params)
    outline(pdir)  # refuses before a run folder exists
    run = _new_run(pdir, "agy_rewrite", lang)
    _common_files(run, pdir, lang)
    cur = script.load(pdir, lang)
    base = (cur or {}).get("version", 0)
    _task(run, "REWRITE.md", "rewrite.md", pdir, lang, base_version=base)
    params["run"], params["base_version"] = run, base
    return agy.argv("Read REWRITE.md in the current folder and do exactly what it says. " + agy.NO_TOOLS)


def rewrite_end(job):
    if job["status"] != "done":
        return
    data = workers._result(job, screen=SCREEN)
    if data is None:
        return
    pid, pdir, lang = _target(job["params"])
    try:
        clean = _clean(pdir, data, reviewed=False)
        v = script.save(pdir, clean, "agy", base=job["params"].get("base_version"), lang=lang)
    except ValueError as e:
        return _refuse(job, str(e))
    record_check(pdir, lang)
    jobs.enqueue("claude_review_lang", {"project": pid, "lang": lang}, pid, "Claude soát kịch bản %s v%d" % (lang.upper(), v))


# ---------------------------------------------------------------- claude_review_lang
def review_build(params):
    pid, pdir, lang = _target(params)
    cur = script.load(pdir, lang)
    if not cur:
        raise ValueError("chưa có kịch bản %s" % lang)
    run = _new_run(pdir, "claude_review_lang", lang)
    _common_files(run, pdir, lang)
    workers._json_file(os.path.join(run, "script.json"), cur)
    workers._json_file(os.path.join(run, "check.json"), record_check(pdir, lang))
    _task(run, "REVIEW_LANG.md", "review_lang.md", pdir, lang)
    params["run"], params["base_version"] = run, cur["version"]
    return workers._claude_argv("REVIEW_LANG.md")


def _flags(data, sids):
    out = []
    for f in data.get("flags") or [] if isinstance(data, dict) else []:
        if not isinstance(f, dict) or f.get("sentence") not in sids:
            raise ValueError("cờ không hợp lệ: %s" % json.dumps(f, ensure_ascii=False)[:120])
        out.append({"sentence": f["sentence"], "issue": str(f.get("issue") or "").strip(),
                    "back_translation_vi": str(f.get("back_translation_vi") or "").strip()})
    return out


def review_end(job):
    claude_box._answers.pop(job["id"], None)
    if job["status"] != "done":
        return
    data = workers._result(job, screen=SCREEN)
    if data is None:
        return
    pid, pdir, lang = _target(job["params"])
    try:
        clean = _clean(pdir, data, reviewed=True)
        clean["flags"] = _flags(data, {s["id"] for _, s in script.sentences(clean)})
        v = script.save(pdir, clean, "claude", base=job["params"].get("base_version"), lang=lang)
    except ValueError as e:
        return _refuse(job, str(e))
    c = record_check(pdir, lang)
    r = c["report"]
    # a number written in words cannot be compared with the facts by code: the owner checks it, never auto
    words = sum(any(x.startswith(script.NUMBER_WORDS_YELLOW) for x in row["reasons"]) for row in r["sentences"])
    if not r["red"] and not c["glossary_misses"] and not c["problems"] and not clean["flags"] and not words:
        script.approve(pdir, "auto", lang=lang)
        inbox.add(pid, "lang_done", "Kịch bản %s v%d tự chốt: kiểm tự động và Claude đều sạch" % (lang.upper(), v),
                  screen=SCREEN, notify_owner=False)
        return
    progress.set_lang(pdir, lang, "script", "wait")
    for f in clean["flags"]:
        inbox.add(pid, "lang_flag", "%s câu %s: %s — dịch lại: %s" % (lang.upper(), f["sentence"], f["issue"], f["back_translation_vi"]),
                  screen=SCREEN, key="langflag:%s:%s:%s" % (pid, lang, f["sentence"]))
    if r["red"] or c["glossary_misses"] or c["problems"] or words:
        inbox.add(pid, "script_approve", "Kịch bản %s v%d chờ bạn (đỏ %d, tên lệch bảng thuật ngữ %d, số viết bằng chữ %d)"
                  % (lang.upper(), v, r["red"], c["glossary_misses"], words), screen=SCREEN, key=script.approve_key(pdir, lang))


# ---------------------------------------------------------------- on-screen labels (dates, names, places) per language
def labels_build(params):
    pid, pdir, lang = _target(params)
    from tools.longform import scenes
    lbls = scenes.own_labels(pdir)
    if not lbls:
        raise ValueError("chưa có nhãn chữ trên màn hình (Claude dựng cảnh trước)")
    run = _new_run(pdir, "agy_labels", lang)
    workers._json_file(os.path.join(run, "labels.json"), {k: v.get("vi", "") for k, v in lbls.items()})
    workers._json_file(os.path.join(run, "glossary.json"), glossary.load(lang))
    _task(run, "LABELS.md", "labels.md", pdir, lang)
    params["run"] = run
    return agy.argv("Read LABELS.md in the current folder and do exactly what it says. " + agy.NO_TOOLS)


def labels_end(job):
    if job["status"] != "done":
        return
    data = workers._result(job)
    if data is None:
        return
    from tools.longform import scenes
    pid, pdir, lang = _target(job["params"])
    if not isinstance(data, dict):
        return _refuse(job, "result.json phải là object")
    try:
        scenes.set_lang_labels(pdir, lang, data)
    except ValueError as e:
        return _refuse(job, str(e))


jobs.register(jobs.Kind("agy_labels", "agy", labels_build, cwd=workers._cwd, on_end=_guarded(labels_end)))
jobs.register(jobs.Kind("agy_rewrite", "agy", rewrite_build, cwd=workers._cwd, on_end=_guarded(rewrite_end)))
jobs.register(jobs.Kind("claude_review_lang", "claude", review_build, cwd=workers._cwd, on_line=claude_box.on_line,
                        on_end=_guarded(review_end)))
