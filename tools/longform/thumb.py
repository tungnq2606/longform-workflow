"""Per-language thumbnail, drawn by Remotion (composition Thumb, 1280x720 still): an approved background, an approved
hero kit pose and the title in that language. Text is never drawn by the image model.

  python -m tools.longform.thumb <project_id> <lang> <bg item> <kit/pose> <title>   (Studio job render_thumb, lane render)

Writes projects/<id>/lang/<code>/upload/thumb.png.
"""
import json
import os
import re
import sys

from tools.longform import claude_box, images, inbox, jobs, paths, project, render

PY = os.path.join(paths.WS, ".venv", "bin", "python")
FONTS = {"ja": "tools/kit/fonts/NotoSansJP-Variable.ttf"}
FONT_OTHER = "tools/kit/fonts/BeVietnamPro-Black.ttf"
HERO = re.compile(r"^([a-z0-9-]+)/([a-z0-9-]+\.[a-z0-9-]+)$")
MAX_TITLE = 100


def props(pdir, lang, bg_item, hero_key, title):
    """{"props", "files", "out"} for the Thumb still, or ValueError with a Vietnamese reason."""
    if lang not in project.load_project(pdir)["languages"]:
        raise ValueError("dự án không có ngôn ngữ %s" % lang)
    title = (title or "").strip() if isinstance(title, str) else ""
    if not title or len(title) > MAX_TITLE or "\x00" in title:
        raise ValueError("tiêu đề thumbnail trống hoặc dài quá %d ký tự" % MAX_TITLE)
    try:
        it = images.get(pdir, bg_item)
    except KeyError:
        raise ValueError("không có ảnh %s" % bg_item)
    final = (it.get("files") or {}).get("final")
    if it.get("type") != "bg" or it.get("state") != "approved" or not final:
        raise ValueError("%s không phải nền đã duyệt" % bg_item)
    m = HERO.match(hero_key or "")
    if not m:
        raise ValueError("tư thế nhân vật không hợp lệ: %s" % hero_key)
    kit_dir = os.path.join(paths.library(), "characters", m.group(1))
    try:
        with open(os.path.join(kit_dir, "kit.json"), encoding="utf-8") as f:
            im = json.load(f)["images"][m.group(2)]
    except (OSError, ValueError, KeyError):
        raise ValueError("bộ nhân vật %s không có tư thế %s" % (m.group(1), m.group(2)))
    hero = "library/characters/%s/%s" % (m.group(1), im["file"])
    font = FONTS.get(lang, FONT_OTHER)
    return {"props": {"bg": final, "hero": hero, "title": title, "lang": lang}, "files": [final, hero, font],
            "out": os.path.join(pdir, "lang", lang, "upload", "thumb.png")}


def render_thumb(pdir, lang, bg_item, hero_key, title):
    p = props(pdir, lang, bg_item, hero_key, title)
    return render.render(pdir, "Thumb", p["out"], p["files"], frame=0, props=p["props"])


def thumb_path(pdir, lang):
    path = os.path.join(pdir, "lang", lang, "upload", "thumb.png")
    return path if os.path.isfile(path) else None


def build(params):
    pid = claude_box.check_project(params.get("project"))
    if pid is None:
        raise ValueError("thiếu dự án")
    pdir = os.path.join(paths.projects(), pid)
    lang, bg, hero, title = params.get("lang"), params.get("bg"), params.get("hero"), params.get("title")
    props(pdir, lang, bg, hero, title)  # refuse at enqueue time, before anything runs
    return [PY, "-m", "tools.longform.thumb", pid, lang, bg, hero, title.strip()]


def on_end(job):
    if job["status"] == "done":
        lang = job["params"]["lang"]
        inbox.add(job["project"], "thumb_done", "Thumbnail %s xong" % lang.upper(), screen="langs",
                  key="thumb:%s:%s" % (job["project"], lang), notify_owner=False)


jobs.register(jobs.Kind("render_thumb", "render", build, on_end=on_end))


if __name__ == "__main__":
    pid_, lang_, bg_, hero_, title_ = sys.argv[1:6]
    print(render_thumb(os.path.join(paths.projects(), pid_), lang_, bg_, hero_, title_))
