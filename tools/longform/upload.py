"""Upload texts per language (Plan 6): title, description, tags and chapters, written by agy, checked by code.

  lang/<code>/upload/upload.md     what the owner copies into YouTube (title, description + chapters, tags, reminder)
  lang/<code>/upload/upload.json   the same texts for Studio

The description has exactly one short sources line (names only, no links) and never an "AI illustration" line: the
owner sets altered/synthetic content = Yes when uploading (spec §3).
"""
import json
import os
import re
import unicodedata

from tools.longform import agy, factbank, inbox, jobs, languages, progress, project, script, workers

SOURCES_LINE = {"vi": "Nguồn:", "en": "Sources:", "ja": "出典:", "de": "Quellen:", "es": "Fuentes:"}
MAX_TITLE, MAX_TAGS, MAX_SOURCES_LINE = 100, 500, 300
AI_LINES = [re.compile(p, re.IGNORECASE) for p in (
    r"minh h[oọ]a b[aằ]ng (ai|tr[ií] tu[eệ] nh[aâ]n t[aạ]o)", r"(t[aạ]o|l[aà]m) b[aằ]ng (ai|tr[ií] tu[eệ] nh[aâ]n t[aạ]o)",
    r"\b(illustrated|generated|created|made|produced) (with|by|using) (an )?ai\b", r"\bai[- ](generated|illustrat\w*|images?|art)\b",
    r"\b(mit|durch) ki (erstellt|generiert|illustriert|gemacht)", r"\bki[- ](generiert|erstellt|bilder|illustration)",
    r"\b(generad|cread|ilustrad|hech)[oa]s? (con|por|mediante) (la )?(ia|ai)\b", r"\bim[aá]genes (de|con) (ia|ai)\b",
    r"(ai|人工知能)(で|による|を使って|を使用して)?.{0,6}(生成|作成|制作|イラスト)",
)]
REMINDER = "Khi upload: đặt nội dung thay đổi/tổng hợp = Có"
SCREEN = "langs"


def _nfc(text):
    return unicodedata.normalize("NFC", text or "")


def validate(texts, lang):
    """Vietnamese problems; empty when the texts can be used."""
    if not isinstance(texts, dict) or not isinstance(texts.get("title"), str) or not isinstance(texts.get("description"), str) \
            or not isinstance(texts.get("tags"), list) or not all(isinstance(t, str) for t in texts["tags"]):
        return ["cần title (chuỗi), description (chuỗi) và tags (danh sách chuỗi)"]
    out = []
    title, desc = _nfc(texts["title"]).strip(), _nfc(texts["description"])
    if not title:
        out.append("tiêu đề trống")
    if len(title) > MAX_TITLE:
        out.append("tiêu đề dài %d ký tự (tối đa %d)" % (len(title), MAX_TITLE))
    if re.search(r"https?:|www\.", desc + " " + title, re.IGNORECASE):
        out.append("mô tả không được có link (http)")
    if any(p.search(desc) for p in AI_LINES):
        out.append('mô tả không được có dòng "minh họa bằng AI" (đặt nội dung tổng hợp = Có khi upload)')
    prefix = SOURCES_LINE.get(lang, "Sources:")
    lines = [ln.strip() for ln in desc.splitlines()]
    src = [ln for ln in lines if ln.startswith(prefix)]
    others = [ln for ln in lines if any(ln.startswith(p) for c, p in SOURCES_LINE.items() if p != prefix)]
    if len(src) != 1 or others:
        out.append('mô tả phải có đúng một dòng nguồn bắt đầu bằng "%s" (có %d)' % (prefix, len(src) + len(others)))
    elif len(src[0]) > MAX_SOURCES_LINE:
        out.append("dòng nguồn quá dài (tối đa %d ký tự)" % MAX_SOURCES_LINE)
    if len(",".join(texts["tags"])) > MAX_TAGS:
        out.append("tags dài quá %d ký tự" % MAX_TAGS)
    return out


def _stamp(sec):
    sec = int(sec)
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return "%d:%02d:%02d" % (h, m, s) if h else "%d:%02d" % (m, s)


def load_timing(pdir, lang):
    try:
        with open(os.path.join(pdir, "lang", lang, "timing.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def chapter_starts(pdir, lang):
    """[(seconds or None, chapter title)] from the language script and Plan 5's timing.json."""
    data = script.load(pdir, lang) or {}
    timing = load_timing(pdir, lang) or {}
    starts = {b["id"]: b.get("start") for b in timing.get("beats", [])}
    out = []
    for ch in data.get("chapters", []):
        first = ch["beats"][0]["id"] if ch.get("beats") else None
        out.append((starts.get(first), ch.get("title", "")))
    return out


def chapters(pdir, lang):
    """YouTube chapter lines ("0:00 Title" first), or "" while there is no timing."""
    rows = [(t, title) for t, title in chapter_starts(pdir, lang) if t is not None]
    if not load_timing(pdir, lang) or not rows:
        return ""
    return "\n".join("%s %s" % (_stamp(0 if i == 0 else t), title) for i, (t, title) in enumerate(rows))


def _dir(pdir, lang):
    d = os.path.join(pdir, "lang", lang, "upload")
    os.makedirs(d, exist_ok=True)
    return d


def write(pdir, lang, texts):
    d = _dir(pdir, lang)
    ch = chapters(pdir, lang)
    desc = texts["description"].rstrip() + ("\n\n" + ch if ch else "")
    md = "# Upload %s\n\n%s\n\n## Tiêu đề\n\n%s\n\n## Mô tả\n\n%s\n\n## Tags\n\n%s\n" % (
        lang.upper(), REMINDER, texts["title"].strip(), desc, ", ".join(t.strip() for t in texts["tags"]))
    for name, body in (("upload.md", md), ("upload.json", json.dumps(dict(texts, chapters=ch), ensure_ascii=False, indent=1))):
        p = os.path.join(d, name)
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            f.write(body)
        os.replace(p + ".tmp", p)
    return os.path.join(d, "upload.md")


def load(pdir, lang):
    try:
        with open(os.path.join(pdir, "lang", lang, "upload", "upload.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def source_names(pdir, data):
    """Names (title, publisher) of the sources behind the facts the approved sentences use. Never URLs."""
    sources, facts = factbank.load(pdir)
    used = {f for _, s in script.sentences(data) for f in s.get("facts", [])}
    seen, out = set(), []
    for fid in sorted(used):
        src = sources.get((facts.get(fid) or {}).get("source"), {})
        key = src.get("id")
        if key and key not in seen:
            seen.add(key)
            out.append({"title": src.get("title", ""), "publisher": src.get("publisher", "")})
    return out


# ---------------------------------------------------------------- agy_upload_texts
def _target(params):
    pid, pdir = workers._project(params)
    lang = params.get("lang")
    if not isinstance(lang, str) or lang not in project.load_project(pdir)["languages"]:
        raise ValueError("ngôn ngữ không hợp lệ cho dự án: %s" % lang)
    return pid, pdir, lang


def build(params):
    pid, pdir, lang = _target(params)
    data = script.load(pdir, lang)
    if not data or not data.get("approved"):
        raise ValueError("kịch bản %s chưa chốt" % lang.upper())
    run = workers._new_run(pdir, "agy_upload_texts_%s" % lang)
    workers._json_file(os.path.join(run, "script.json"), data)
    workers._json_file(os.path.join(run, "chapters.json"),
                       [{"title": title, "start": t} for t, title in chapter_starts(pdir, lang)])
    workers._json_file(os.path.join(run, "sources.json"), source_names(pdir, data))
    workers._task(run, "UPLOAD.md", "upload_texts.md", pdir, lang=lang, lang_name=languages.load_languages()[lang].name,
                  sources_prefix=SOURCES_LINE.get(lang, "Sources:"))
    params["run"] = run
    return agy.argv("Read UPLOAD.md in the current folder and do exactly what it says. " + agy.NO_TOOLS)


def end(job):
    if job["status"] != "done":
        return
    data = workers._result(job, screen=SCREEN)
    if data is None:
        return
    pid, pdir, lang = _target(job["params"])
    problems = validate(data, lang)
    if problems:
        return workers._refuse(job, "; ".join(problems), SCREEN)
    write(pdir, lang, {"title": data["title"].strip(), "description": data["description"].strip(),
                       "tags": [t.strip() for t in data["tags"] if t.strip()]})
    progress.set_step(pdir, "upload", "wait")
    inbox.add(pid, "upload_ready", "Text upload %s sẵn sàng: xem và copy" % lang.upper(), screen=SCREEN,
              key="upload:%s:%s" % (pid, lang), notify_owner=False)


def _guarded(job):
    try:
        end(job)
    except Exception as e:  # noqa: BLE001
        workers._refuse(job, "lỗi khi nhập kết quả: %s" % e, SCREEN)


jobs.register(jobs.Kind("agy_upload_texts", "agy", build, cwd=workers._cwd, on_end=_guarded))
