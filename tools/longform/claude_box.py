"""Studio's Claude box: the owner's message becomes a `claude -p` job (Claude Code on the owner's subscription).

One resumable session per project (projects/<id>/.studio/session) or one general session when no project is open.
Permissions come from config/studio.json: acceptEdits plus an allowed-tools list, never skip-permissions.
History for the UI is projects/<id>/.studio/claude.jsonl (last 30 lines shown).
"""
import json
import os
import re
import threading
import time
import uuid

from tools.longform import jobs, paths

PROJECT_ID = re.compile(r"^\d{3}-[a-z0-9-]+$")
SESSION_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
SAFE_MODES = ("acceptEdits", "default", "plan")  # never bypassPermissions, even if the config file is edited
MAX_MESSAGE = 8000
_answers = {}  # job id -> assistant texts seen so far
_lock = threading.Lock()


def config():
    with open(os.path.join(paths.config(), "studio.json"), encoding="utf-8") as f:
        cfg = json.load(f)["claude"]
    if cfg.get("permission_mode") not in SAFE_MODES:
        raise ValueError("config/studio.json: permission_mode phải là một trong %s" % ", ".join(SAFE_MODES))
    if any(not isinstance(t, str) or t.startswith("-") for t in cfg.get("allowed_tools", [])):
        raise ValueError("config/studio.json: allowed_tools có mục không hợp lệ")
    return cfg


def saved_session(project):
    """The session id of the project's last finished conversation, or None (a broken file counts as none)."""
    try:
        sid = open(os.path.join(session_dir(project), "session")).read().strip()
    except OSError:
        return None
    return sid if SESSION_ID.match(sid) else None


def check_project(project):
    if project is None:
        return None
    if not isinstance(project, str) or not PROJECT_ID.match(project) \
            or not os.path.isfile(os.path.join(paths.projects(), project, "project.json")):
        raise ValueError("không có dự án %s" % project)
    return project


def session_dir(project):
    d = os.path.join(paths.projects(), project, ".studio") if project else os.path.join(paths.state(), "claude-general")
    os.makedirs(d, exist_ok=True)
    return d


def system_prompt(project):
    where = "the project folder projects/%s" % project if project else "the workspace (no project open)"
    return ("You are called from the owner's Studio (long-form history video workflow). Work on %s. Follow CLAUDE.md. "
            "The owner reads Vietnamese: answer briefly in Vietnamese. Never publish, push or delete anything. "
            "Images only through tools/longform/imagegen.py (agy)." % where)


def _append(project, role, text):
    with open(os.path.join(session_dir(project), "claude.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"role": role, "text": text, "at": time.strftime("%H:%M")}, ensure_ascii=False) + "\n")


def build(params):
    message = params.get("message")
    if not isinstance(message, str) or not message.strip() or len(message) > MAX_MESSAGE:
        raise ValueError("tin nhắn trống hoặc dài quá %d ký tự" % MAX_MESSAGE)
    if "\x00" in message:
        raise ValueError("tin nhắn có ký tự không hợp lệ")
    project = check_project(params.get("project"))
    cfg = config()
    prompt = " " + message if message.startswith("-") else message  # a leading "-" would be read as a CLI flag
    argv = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
            "--permission-mode", cfg["permission_mode"], "--append-system-prompt", system_prompt(project)]
    if params.get("model") in cfg["models"]:
        argv += ["--model", params["model"]]
    sid = saved_session(project)
    # A new session id is saved only when that job finishes well (on_end), so a failed first message never pins
    # the box to a session that claude never created.
    argv += ["--resume", sid] if sid else ["--session-id", str(uuid.uuid4())]
    argv += ["--allowedTools"] + cfg["allowed_tools"]
    _append(project, "owner", message)
    return argv


def on_line(job, line):
    try:
        ev = json.loads(line)
    except ValueError:
        return line
    if not isinstance(ev, dict):
        return line
    if ev.get("type") == "assistant":
        out = []
        for c in ev.get("message", {}).get("content", []):
            if c.get("type") == "text":
                out.append(c["text"])
                with _lock:
                    _answers.setdefault(job["id"], []).append(c["text"])
            elif c.get("type") == "tool_use":
                inp = c.get("input", {})
                out.append("  → %s %s" % (c.get("name"), (inp.get("command") or inp.get("file_path") or inp.get("pattern") or "")[:160]))
        return "\n".join(out) if out else None
    if ev.get("type") == "result":
        return "[xong: %s, %.0f s]" % (ev.get("subtype"), (ev.get("duration_ms") or 0) / 1000)
    return None


def on_end(job):
    with _lock:
        texts = _answers.pop(job["id"], [])
    project = job["params"].get("project")
    argv = job.get("argv") or []
    if job.get("status") == "done" and "--session-id" in argv:
        with open(os.path.join(session_dir(project), "session"), "w") as f:
            f.write(argv[argv.index("--session-id") + 1])
    _append(project, "claude", texts[-1] if texts else "(không có trả lời)")


def history(project):
    p = os.path.join(session_dir(check_project(project)), "claude.jsonl")
    try:
        with open(p, encoding="utf-8") as f:
            return [json.loads(l) for l in f.read().splitlines() if l.strip()][-30:]
    except OSError:
        return []


jobs.register(jobs.Kind("claude", "claude", build, on_line=on_line, on_end=on_end))
