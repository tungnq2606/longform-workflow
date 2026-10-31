# Plan 2: Studio shell — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the old Shorts-era dashboard with a new long-form "Studio": a home page with the "🔔 Cần bạn" inbox and project list, a "Video mới" dialog, a project page with step bar and language strip, and a bottom bar with the job list and a Claude box. Everything sits on a disk-backed job queue with pause/resume and Telegram alerts.

**Architecture:** The logic lives in small Python modules in `tools/longform/`, each tested on its own:
- `inbox.py`: items waiting for the owner.
- `jobs.py`: the disk queue and its runner.
- `progress.py`: step and language status.
- `claude_box.py`: the `claude -p` command and session history.

`studio/server.py` is a thin stdlib HTTP layer over those modules. It listens on `127.0.0.1` only and rejects cross-site requests. The UI is plain HTML + ES modules in `studio/static/`, with no build step. Pure UI helpers sit in `lib.js`, tested with `node --test`.

Screens owned by later plans show a "Phần N" placeholder:
- Kịch bản: Plan 3
- Hình ảnh: Plan 4
- Cảnh: Plan 5
- Ngôn ngữ: Plan 6
- Thư viện: Plan 4

**Tech Stack:** Python 3.9 stdlib (`http.server`, `threading`, `subprocess`, `fcntl`) + the existing `.venv`; vanilla JS ES modules; Node 26 `node --test` for `lib.js`; Claude Code CLI `claude -p` on the owner's subscription.

**Spec:** `docs/superpowers/specs/2026-10-31-longform-workflow-design.md` (§3 constraints, §4.3 steps, §4.9, §4.10) · Roadmap: `docs/superpowers/plans/2026-10-31-longform-roadmap.md` · Mockup: `.superpowers/brainstorm/34991-1793441859/content/layout-v2.html`

## Global Constraints

- Workspace root `WS = /Users/quoctung/Documents/AI/youtube-skills-workspace`. Archive root `/Users/quoctung/Documents/AI/archive/2026-10-31/`: move there, never delete.
- Studio listens on `127.0.0.1` only (port from `config/studio.json`, default `8765`); never `0.0.0.0`.
- Claude runs with `--permission-mode acceptEdits` and an `--allowedTools` list from config. Never `--dangerously-skip-permissions`.
- Job commands are argv lists built server-side from a registered job kind. The browser never sends a command string.
- Telegram secret moves to `config/secrets/telegram.json` (already gitignored). Never print or commit it.
- Queue rule (spec §3): state on disk; pause lets running jobs finish and starts nothing new; nothing blocks anything else.
- UI text is Vietnamese. File names, code and JSON keys are English.
- No new macOS-only calls (`sips`, Swift, `osascript`, `open`, launchd); no new `.sh` scripts; no new pip/npm dependencies.
- Commits end with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Tests:
  - `.venv/bin/python -m unittest discover -s tools/longform/tests -v`
  - `node --test studio/static/`
  - `cd tools/anim && node --test src/longform/ && npx tsc --noEmit -p .` (must stay green)

## Review Focus

1. **Studio restarts (crash, reboot) while a job runs.** The job ends as `interrupted` with an inbox item. It never stays "running" forever and never reruns silently (Task 3, `test_recover_interrupted`).
2. **A web page on another site POSTs to `127.0.0.1:8765`** (form/fetch CSRF, or DNS rebinding with a foreign `Host`). Expect 403; no job starts. Claude can edit files, so this matters (Task 6, `test_rejects_foreign_origin`, `test_rejects_foreign_host`, `test_rejects_non_json_post`).
3. **Pause while 3 jobs run.** They finish; queued jobs stay queued; none starts until resume (Task 3, `test_pause_lets_running_finish`).
4. **Two "Video mới" for the same title, back to back.** Expect two projects with consecutive numbers; nothing is overwritten (Task 4, `test_next_number_twice`).
5. **`claude` not on PATH, or no Telegram secret.** The job fails with a Vietnamese message plus an inbox item; the inbox and the queue keep working (Task 3, `test_missing_binary_fails_cleanly`; Task 2, `test_add_without_telegram`).

---

### Task 1: Retire the old dashboard, move secrets and brand, point Telegram at Studio

**Files:**
- Move (not delete):
  - `dashboard/` (everything except `dashboard/secrets/`) → `<archive>/workspace-code/dashboard/`
  - `tools/workqueue.py` → `<archive>/workspace-code/tools/`
  - `channels/vn-history/brand/` → `/Users/quoctung/Documents/AI/brand/cong-truong-lich-su/`
- Move: `dashboard/secrets/telegram.json` → `config/secrets/telegram.json` (use `mv`; never `cat` it)
- Modify: `tools/notify.py`, `.gitignore`, `<archive>/README.md`
- Create: `config/studio.json`, `studio/__init__.py`
- Test: `tools/longform/tests/test_notify.py`

**Interfaces:**
- Produces:
  - `notify.CONF = <WS>/config/secrets/telegram.json`
  - `notify.studio_url() -> str` (`http://127.0.0.1:<port>` from `config/studio.json`)
  - `notify.link(project_id: str | None, screen: str = "") -> str`, giving `<url>/#/p/<id>/<screen>` (or `<url>/#/` when `project_id` is None; no trailing `/` when screen is empty)
  - `notify.send(text) -> bool`: unchanged contract, never raises
  - `config/studio.json`:
    `{"port": 8765, "lanes": {"claude": 1, "agy": 4, "render": 1, "cpu": 2}, "claude": {"permission_mode": "acceptEdits", "models": ["opus", "sonnet"], "allowed_tools": [...]}}`
    `allowed_tools` copies the old list, minus `Bash(sips *)` and `Bash(python3 dashboard/*)`, plus `Bash(.venv/bin/python *)` and `Bash(npx tsc *)`.

- [ ] **Step 1: Write failing tests** in `test_notify.py`:
  - `test_conf_path`: `notify.CONF` ends with `config/secrets/telegram.json`.
  - `test_link_project`: `notify.link("001-bach-dang", "images") == "http://127.0.0.1:8765/#/p/001-bach-dang/images"`.
  - `test_link_home`: `notify.link(None) == "http://127.0.0.1:8765/#/"`.
  - `test_send_without_secret`: with `CONF` patched to a missing file and the env vars unset, `send("x") is False`.
- [ ] **Step 2: Run them.** Run: `.venv/bin/python -m unittest tools.longform.tests.test_notify -v`. Expected: FAIL (`AttributeError: link`, wrong CONF).
- [ ] **Step 3: Implement.**
  - Do the moves with `mv`.
  - Update `notify.py`: drop `video_link` and `DASH_URL`, read the port from `config/studio.json`.
  - Import `notify.py` as `from tools import notify`. `tools/` has no `__init__.py`, so it works as a namespace package, the same way `tools.longform` already imports.
  - Add `projects/*/.studio/` and `studio/state/` to `.gitignore`.
  - Append the moved items to the archive README.
- [ ] **Step 4: Run tests.**
  - Same command. Expected: PASS.
  - Also run `git status --short | grep -c secrets`. Expected: `0`.
- [ ] **Step 5: Commit** `chore: retire old dashboard; Telegram secret in config/secrets; brand out of workflow`.

---

### Task 2: Inbox ("🔔 Cần bạn")

**Files:**
- Create: `tools/longform/inbox.py`
- Modify: `tools/longform/paths.py`
- Test: `tools/longform/tests/test_inbox.py`

**Interfaces:**
- Produces:
  - `paths.state() -> str`: `<root>/studio/state`, created on demand.
  - `inbox.add(project: str | None, kind: str, text: str, screen: str = "", key: str | None = None, notify_owner: bool = True) -> dict`
    - Returns the item `{"id", "project", "kind", "text", "screen", "key", "created" (ISO seconds), "done": false}`.
    - When an open item with the same `key` exists: update its `text`, keep its `id`, do not notify again.
    - On a new item with `notify_owner=True`: call `notify.send("🔔 <text>\n<notify.link(project, screen)>")`.
  - `inbox.open_items(project: str | None = None) -> list[dict]`: newest first.
  - `inbox.resolve(item_id: str) -> bool` and `inbox.resolve_key(key: str) -> bool`.
- Storage: `<state>/inbox.json`, written atomically (temp file + `os.replace`) under an `fcntl.flock` on `<state>/inbox.json.lock`. Later plans add items from CLI tools while Studio runs, so the lock is cross-process.
- Kinds used now: `job_failed`, `job_interrupted`. Later plans add `image_review`, `script_approve`, `missing_voice`, `name_pronunciation`, etc. `kind` is free text, and the UI maps known kinds to an emoji (Task 7).

- [ ] **Step 1: Write failing tests.** Each test uses a temp `LONGFORM_ROOT` and patches `inbox.notify.send` with a recorder.
  - `test_add_and_list`: two adds, then `open_items()` returns 2 items, newest first.
  - `test_key_dedupes`: two adds with `key="img:BG08"` leave 1 open item with the second text, and `send` was called once.
  - `test_resolve`: after `resolve(id)`, `open_items() == []`.
  - `test_resolve_key`.
  - `test_filter_project`.
  - `test_add_without_telegram`: patch `send` to return `False`; `add` still stores the item.
  - `test_survives_reload`: after `importlib.reload(inbox)`, items are still there.
- [ ] **Step 2: Run.** Run: `.venv/bin/python -m unittest tools.longform.tests.test_inbox -v`. Expected: FAIL, ImportError.
- [ ] **Step 3: Implement** `inbox.py` and `paths.state()`.
- [ ] **Step 4: Run.** Same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: Studio inbox on disk with Telegram alert`.

---

### Task 3: Disk-backed job queue with lanes, pause and recovery

**Files:**
- Create: `tools/longform/jobs.py`
- Test: `tools/longform/tests/test_jobs.py`

**Interfaces:**
- Consumes: `inbox.add`, `paths.state()`.
- Produces:
  - `jobs.Kind(name: str, lane: str, build: Callable[[dict], list[str]], cwd: str = WS, on_line: Callable[[dict, str], str | None] | None = None, on_end: Callable[[dict], None] | None = None)`
    - `build` turns params into argv and raises `ValueError` on bad params.
    - `on_line` maps a raw stdout line to the text written to the job log; `None` drops the line.
  - `jobs.register(kind: Kind) -> None`; `jobs.KINDS: dict[str, Kind]`.
  - `jobs.enqueue(kind: str, params: dict, project: str | None, label: str) -> dict`: validates through `build` at enqueue time, so a bad request fails in the HTTP call, not later.
  - Job record `<state>/jobs/<id>.json`:
    - Fields: `{"id", "kind", "lane", "params", "argv", "project", "label", "status", "created", "started", "ended", "exit", "error", "pid"}`.
    - `status` is one of `queued|running|done|failed|stopped|interrupted`.
  - Job log `<state>/jobs/<id>.log` holds the `on_line` output.
  - `jobs.list_jobs(limit: int = 50) -> list[dict]`: running first, then queued (oldest first), then finished (newest first).
  - `jobs.read_log(job_id: str, offset: int = 0) -> tuple[str, int]`: returns text from the byte offset and the new offset.
  - `jobs.stop(job_id) -> bool`:
    - queued: becomes `stopped`.
    - running: SIGTERM, then SIGKILL after 5 s, then `stopped`.
  - Pause:
    - `jobs.set_paused(on: bool, reason: str = "") -> None` and `jobs.paused() -> dict` (`{"on", "reason", "since"}`) in `<state>/pause.json`.
    - Pause changes no job; it only stops the runner from starting new ones.
  - `jobs.Runner(lanes: dict[str, int], poll: float = 0.5)`, with `.start()`, `.stop()` and `.tick()` (one scheduling pass, used by tests).
    - Each tick:
      1. Unless paused, start the oldest queued job of each lane while `running(lane) < lanes[lane]`.
      2. Every job runs in a thread: `subprocess.Popen(argv, cwd, stdout=PIPE, stderr=STDOUT, text=True)`.
    - On exit:
      - Exit 0 becomes `done`; anything else becomes `failed`.
      - `failed` calls `inbox.add(project, "job_failed", "Job hỏng: <label> (mã <exit>)", key="job:<id>")`.
      - `on_end(job)` is called after the status is written.
    - A missing binary (`FileNotFoundError`) becomes `failed` with `error="không tìm thấy lệnh <argv[0]>"` plus the inbox item.
  - `jobs.recover() -> int`, called once at Studio start:
    - Every `running` record becomes `interrupted`, with an inbox item `"Job bị ngắt (Studio tắt giữa chừng): <label>"` (key `job:<id>`).
    - Returns the count. Never requeues.

- [ ] **Step 1: Write failing tests.** Use a temp `LONGFORM_ROOT`. Register test kinds whose `build` returns `[sys.executable, "-c", <code>]`, and drive the runner with `tick()` plus a wait helper on job status (timeout 10 s).
  - `test_enqueue_validates`: `build` raises `ValueError`, so `enqueue` raises and nothing is written.
  - `test_runs_and_logs`: `print('hi')` ends `done`, and `read_log` returns `"hi\n"`.
  - `test_lane_limit`: lane `x` limit 1, two `sleep 0.5` jobs; right after the first tick, exactly one is `running`.
  - `test_lanes_independent`: lane `x` and lane `y` jobs run at the same time.
  - `test_pause_lets_running_finish`: 3 jobs on a lane with limit 3, plus 1 queued.
    - Tick, then `set_paused(True)`.
    - The 3 running jobs end `done`; the 4th is still `queued` after further ticks.
    - `set_paused(False)` plus a tick starts the 4th.
  - `test_failure_goes_to_inbox`: `exit(3)` gives `failed`, `exit == 3`, and one open inbox item of kind `job_failed`.
  - `test_missing_binary_fails_cleanly`: argv `["/nonexistent/x"]` gives `failed`, an error containing `không tìm thấy lệnh`, and an inbox item.
  - `test_stop_running`.
  - `test_stop_queued`.
  - `test_recover_interrupted`: write a record with `status="running"`; `recover()` returns 1, and the status becomes `interrupted` with an inbox item.
  - `test_on_line_filters`: `on_line` returns `None` for lines starting with `#`, so those lines are not in the log.
- [ ] **Step 2: Run.** Run: `.venv/bin/python -m unittest tools.longform.tests.test_jobs -v`. Expected: FAIL, ImportError.
- [ ] **Step 3: Implement** `jobs.py`.
  - Records are written atomically (temp + `os.replace`).
  - One in-process `threading.Lock` guards scheduling. Only Studio runs jobs, so no cross-process lock is needed for records.
- [ ] **Step 4: Run.** Same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: disk job queue with lanes, pause and crash recovery`.

---

### Task 4: Project progress (step bar, language strip) and "Video mới"

**Files:**
- Create: `tools/longform/progress.py`
- Modify: `tools/longform/project.py`
- Test: `tools/longform/tests/test_progress.py`

**Interfaces:**
- Consumes: `project.create_project`, `project.load_project`, `project.list_projects`, `project.ascii_slug`.
- Produces:
  - `progress.STEPS`:
    `[("topic","Đề tài"), ("script","Kịch bản"), ("images","Hình ảnh"), ("scenes","Cảnh"), ("langs","Ngôn ngữ"), ("render","Render"), ("upload","Upload")]` (spec §4.3).
  - `progress.LANG_PARTS = [("script","kịch bản"), ("voice","giọng"), ("render","render")]`.
  - `progress.STATES = ("todo", "doing", "wait", "done")`. `wait` means waiting for the owner.
  - `progress.get(pdir) -> dict`:
    - Returns `{"steps": [{"id","label","state"}], "langs": [{"code","parts": {part: state}}], "done": int, "total": 7}`.
    - Reads the optional `project.json` keys `"steps": {id: state}` and `"lang_status": {code: {part: state}}`.
    - Missing keys mean `todo`.
  - `progress.set_step(pdir, step_id, state)` and `progress.set_lang(pdir, code, part, state)`:
    - Rewrite `project.json` atomically.
    - Raise `ValueError` on an unknown step, part, state or language.
    - Later plans' tools call these.
  - `project.next_number() -> int`: highest existing `NNN` plus 1 (1 when there are none; `000-spike` counts as 0).
  - `project.new_project(title: str, langs: list[str]) -> str`:
    - Slug is `ascii_slug(title)`; raises `ValueError("tên không có chữ Latin")` when the slug is empty.
    - Number is `next_number()`.
    - Retries with the next number on `FileExistsError` (at most 5 times).

- [ ] **Step 1: Write failing tests** (temp `LONGFORM_ROOT` with `config/languages.json` copied in):
  - `test_default_todo`.
  - `test_set_step_roundtrip`.
  - `test_set_step_unknown_raises`.
  - `test_lang_strip_follows_languages`: a project with `["en","ja"]` shows codes `vi,en,ja`.
  - `test_done_count`.
  - `test_next_number_twice`: two `new_project("Bạch Đằng", [])` give `001-bach-dang` and `002-bach-dang`.
  - `test_new_project_empty_slug_raises`: title `"白藤江"`.
- [ ] **Step 2: Run.** Run: `.venv/bin/python -m unittest tools.longform.tests.test_progress -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the whole Python suite. Expected: PASS (the Plan 1 `test_project` still passes).
- [ ] **Step 5: Commit** `feat: project step and language status, Video mới numbering`.

---

### Task 5: Claude box (headless `claude -p`, one session per project)

**Files:**
- Create: `tools/longform/claude_box.py`
- Test: `tools/longform/tests/test_claude_box.py`

**Interfaces:**
- Consumes: `jobs.Kind`, `jobs.register`, `config/studio.json`.
- Produces:
  - `claude_box.session_dir(project: str | None) -> str`:
    - `projects/<id>/.studio/` for a project.
    - `<state>/claude-general/` when there is no project.
  - `claude_box.system_prompt(project: str | None) -> str`, in English. It says:
    - The request comes from the owner's Studio.
    - The work is on `projects/<id>` (or the workspace).
    - Follow `CLAUDE.md`.
    - Answer briefly in Vietnamese.
    - Never publish, push or delete; images only through `tools/longform/imagegen.py` (agy).
  - `claude_box.build(params: dict) -> list[str]`:
    - `params = {"message": str (1..8000 chars), "project": str | None, "model": str | None}`.
    - Argv: `["claude","-p",message,"--output-format","stream-json","--verbose","--permission-mode",<cfg>,"--append-system-prompt",<sp>,"--allowedTools",*cfg_tools]`.
    - Adds `["--model", m]` only when `m` is in the config's `models`.
    - Adds `["--resume", sid]` when `<session_dir>/session` exists; otherwise a new uuid4 with `["--session-id", sid]`, saved to that file.
    - Raises `ValueError` on an empty or oversized message, or an unknown project id (it must be an existing `projects/<id>/project.json`).
  - `claude_box.on_line(job, line) -> str | None`:
    - Parses stream-json.
    - Assistant text becomes the text.
    - `tool_use` becomes `"  → <name> <command|file_path|pattern, ≤160 chars>"`.
    - `result` becomes `"[xong: <subtype>, <s> s]"`.
    - Other events become `None`.
    - Non-JSON lines are returned unchanged.
  - `claude_box.history(project) -> list[dict]` reads `<session_dir>/claude.jsonl`: the last 30 `{"role": "owner"|"claude", "text", "at"}`.
    - `build` appends the owner line.
    - `on_end` appends the last assistant text, or `"(không có trả lời)"`.
  - Registers kind `claude` on lane `claude` at import.

- [ ] **Step 1: Write failing tests:**
  - `test_build_new_session`: a session file is created and `--session-id` is present.
  - `test_build_resumes`: a second build uses `--resume` with the same id.
  - `test_no_skip_permissions`: `"--dangerously-skip-permissions" not in argv`, and the value after `--permission-mode` equals `"acceptEdits"`.
  - `test_model_whitelist`: `"opus"` gives `--model opus`; `"x"` gives no `--model`.
  - `test_rejects_bad_project`: `"../etc"` raises `ValueError`.
  - `test_rejects_empty_message`.
  - `test_on_line_text_and_tool`: uses canned stream-json lines.
  - `test_history_roundtrip`: `build`, then `on_end` with a fake job holding collected text, gives 2 history entries.
- [ ] **Step 2: Run.** Run: `.venv/bin/python -m unittest tools.longform.tests.test_claude_box -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** The collected answer lives in a per-job dict keyed by job id, filled by `on_line`.
- [ ] **Step 4: Run.** Same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: Claude box job kind with per-project session`.

---

### Task 6: Studio HTTP server (API + guard)

**Files:**
- Create: `studio/server.py`, `studio/__main__.py` (runs `server.main()`)
- Test: `tools/longform/tests/test_server.py`

**Interfaces:**
- Consumes: Tasks 2–5.
- Produces:
  - `studio.server.make_server(port: int, runner: jobs.Runner | None) -> ThreadingHTTPServer`, bound to `("127.0.0.1", port)`.
  - `main()`:
    - `jobs.recover()`.
    - Start a `Runner(cfg["lanes"])`.
    - Serve forever.
    - Print `Studio: http://127.0.0.1:<port>`.
  - Start command: `.venv/bin/python -m studio`.
- Guard, applied to every request before routing:
  - `Host` must be `127.0.0.1:<port>` or `localhost:<port>`; otherwise 403 (DNS rebinding).
  - On POST:
    - If `Origin` is present, it must be `http://127.0.0.1:<port>` or `http://localhost:<port>`.
    - `Content-Type` must start with `application/json`, which forces a CORS preflight that Studio never answers.
    - Otherwise 403.
  - Static files are served only from `studio/static/`, resolved with `realpath`; anything outside gives 404.
- API (JSON in, JSON out; errors are `{"error": "<Vietnamese text>"}` with 400/404):

| Method | Path | Does |
|---|---|---|
| GET | `/` | `studio/static/index.html` |
| GET | `/static/<file>` | static file |
| GET | `/api/home` | `{"inbox": open_items(), "projects": [{id,title,languages,done,total}], "paused": paused()}` |
| GET | `/api/languages` | `[{code,name}]` from `languages.load_languages()` |
| POST | `/api/projects` | `{"title","languages"}` → `new_project` → `{"id"}` |
| GET | `/api/projects/<id>` | `{"project": load_project, "progress": progress.get, "inbox": open_items(id)}` |
| GET | `/api/jobs` | `list_jobs()` |
| GET | `/api/jobs/<id>/log?offset=N` | `{"text","offset"}` |
| POST | `/api/jobs/<id>/stop` | `{"ok"}` |
| POST | `/api/pause` | `{"on": bool}` → `set_paused(on, "Bạn bấm Tạm dừng")` |
| POST | `/api/claude` | `{"message","project","model"}` → `enqueue("claude", ...)` → job |
| GET | `/api/claude/history?project=<id>` | `history(project)` |
| POST | `/api/inbox/<id>/done` | `resolve(id)` |

  - `<id>` for projects must match `^\d{3}-[a-z0-9-]+$` and exist; job and inbox ids must match `^[0-9a-f]{32}$`.

- [ ] **Step 1: Write failing tests.** Start `make_server(0, None)` in a thread with a temp `LONGFORM_ROOT`, and send requests with `http.client` so headers are set exactly.
  - `test_binds_localhost_only`: `server.server_address[0] == "127.0.0.1"`.
  - `test_home_lists_projects_and_inbox`.
  - `test_create_project_then_get`.
  - `test_rejects_foreign_origin`: POST `/api/claude` with `Origin: https://evil.example` gives 403, and `list_jobs() == []`.
  - `test_rejects_foreign_host`: GET `/api/home` with `Host: evil.example:8765` gives 403.
  - `test_rejects_non_json_post`: `Content-Type: text/plain` gives 403.
  - `test_bad_project_id_404`: `/api/projects/..%2F..%2Fetc` gives 404.
  - `test_static_traversal_404`: `/static/../server.py` gives 404.
  - `test_pause_endpoint`.
  - `test_claude_enqueues_job`: with `jobs.KINDS["claude"]` replaced by a fake kind, the job is `queued` and `project` is set.
- [ ] **Step 2: Run.** Run: `.venv/bin/python -m unittest tools.longform.tests.test_server -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `studio/server.py` (stdlib only).
- [ ] **Step 4: Run** the whole Python suite. Expected: PASS.
- [ ] **Step 5: Commit** `feat: Studio HTTP API bound to localhost with cross-site guard`.

---

### Task 7: Studio UI (home, Video mới, project page, job bar, Claude box)

**Files:**
- Create: `studio/static/index.html`, `studio/static/style.css`, `studio/static/app.js`, `studio/static/lib.js`
- Test: `studio/static/lib.test.js`

**Interfaces:**
- Consumes: the Task 6 API.
- Produces (`lib.js`, pure, no DOM):
  - `route(hash: string) -> {screen: "home"|"project"|"library", id?: string, tab?: string}`.
    - `"#/"` and `""` give home.
    - `"#/p/001-x"` gives project with tab `"overview"`.
    - `"#/p/001-x/images"` gives tab `"images"`.
    - `"#/library"` gives library.
    - Unknown input gives home.
  - `stateIcon(state) -> string`: `todo ⬜`, `doing ▶`, `wait ❓`, `done ✅`.
  - `kindIcon(kind) -> string`: `job_failed ❌`, `job_interrupted ⚠️`, `image_review 🖼️`, `script_approve ✍️`, `missing_voice 🎙️`, `name_pronunciation 🔤`, otherwise `🔔`.
  - `progressBar(done, total, width=7) -> string`: `▓` and `░` cells, e.g. `progressBar(3,7) === "▓▓▓░░░░"`.
  - `jobLine(job) -> string`: `"<icon> <label> · <status vi>"` with status words `chờ`, `đang chạy`, `xong`, `hỏng`, `đã dừng`, `bị ngắt`.
- Layout (mockup `layout-v2.html` §1–2, plus the old bottom bar):
  - **Home** (`#/`):
    - Header "Công xưởng video dài", a pause toggle and a "Thư viện" link.
    - "🔔 Cần bạn (N)": rows `<kindIcon> <text> · <project>`. Clicking a row goes to `#/p/<project>/<screen>`; the "Xong" button calls `/api/inbox/<id>/done`.
    - "Dự án": rows `<id> <title> <progressBar> <done>/7 · <LANGS>` and a "+ Video mới" button.
  - **Video mới**: a dialog with title input and language checkboxes from `/api/languages`; `vi` is checked and disabled. On success it goes to `#/p/<id>`.
  - **Project** (`#/p/<id>`):
    - Title.
    - Step bar from `progress.steps` (`<stateIcon> <label>` joined by ` → `). Clicking a step opens its tab.
    - Language strip `VI ✅ giọng · EN ⏳ kịch bản …` from `progress.langs`.
    - The project's own "Cần bạn" items.
    - Tabs `script|images|scenes|langs`, each showing "Màn hình này làm ở Phần N" (3, 4, 5, 6).
  - **Library** (`#/library`): a placeholder "Phần 4".
  - **Bottom bar** (every screen):
    - The job list (running and queued plus the last 5 finished), with ⏹ on running and queued jobs.
    - Clicking a job opens its log, which polls `/log?offset`.
    - The Claude box: a textarea, model select from config, and "Gửi". It sends to `/api/claude` with the current project, or none on home, and shows that project's history.
  - Polling: `/api/home` or `/api/projects/<id>` and `/api/jobs` every 2 s while the tab is visible (`document.visibilityState`).
  - Every request uses `fetch` with `Content-Type: application/json`. User text goes in through `textContent` only, never `innerHTML`.
- [ ] **Step 1: Write failing tests** in `lib.test.js` (`node:test` + `node:assert`):
  - The route cases above.
  - The `progressBar(3,7)` and `progressBar(0,7)` / `progressBar(7,7)` edges.
  - All six `jobLine` statuses.
  - `kindIcon` fallback.
- [ ] **Step 2: Run.** Run: `node --test studio/static/`. Expected: FAIL (cannot find `lib.js`).
- [ ] **Step 3: Implement** `lib.js`, then `index.html`, `style.css` and `app.js`.
  - Use a light, warm palette that matches the channel style (paper background, ink text, one accent).
  - Readable at 1280 px wide; usable on a phone at 390 px (single column, bottom bar collapses).
- [ ] **Step 4: Run** `node --test studio/static/`. Expected: PASS.
- [ ] **Step 5: Smoke check.**
  - Start `.venv/bin/python -m studio` in the background.
  - `curl -s 127.0.0.1:8765/api/home` returns JSON listing `000-spike`.
  - Create a test project through `POST /api/projects`: `{"title":"Thử Studio","languages":["en"]}`.
  - Enqueue a Claude box message `"Trả lời đúng một chữ: ok"` on it; the job ends `done` and the history has a `claude` entry.
  - Then move the test project to `<archive>/` (never delete).
- [ ] **Step 6: Commit** `feat: Studio UI: home inbox, Video mới, project page, job bar, Claude box`.

---

### Task 8: Docs and owner check

**Files:**
- Modify: `CLAUDE.md` (folder map: `studio/`, `config/studio.json`, `config/secrets/`; old `dashboard/` line removed; start command)
- Rewrite: `HANDOFF.md` for the long-form workflow. The old file moves to the archive.
- Create: `studio/README.md`. Cover:
  - start/stop;
  - port;
  - lanes;
  - how a later plan registers a job kind and adds inbox items;
  - the security model: localhost only, cross-site guard, no skip-permissions; remote access later only through Tailscale plus a password.
- Test: the full suites.

**HANDOFF.md** must cover:
- who the owner is (Vietnamese replies, works alone, Claude subscription plus Google Ultra);
- the spec, roadmap and current plan paths;
- the division of labour (agy: sources, first draft, all images; Claude: script review, Remotion);
- the rules in `CLAUDE.md`;
- how to start Studio;
- what is done (Plans 1–2) and what is next.
Keep it under 150 lines.

- [ ] **Step 1: Write the docs.**
- [ ] **Step 2: Run all suites:** `bash -c '.venv/bin/python -m unittest discover -s tools/longform/tests && node --test studio/static/ && cd tools/anim && node --test src/longform/ && npx tsc --noEmit -p .'`. Expected: all pass.
- [ ] **Step 3: Owner check.**
  - Start Studio and send the owner the link `http://127.0.0.1:8765`. Also send a Telegram test through `inbox.add(None, "test", "Studio đã chạy", notify_owner=True)`, then resolve it.
  - Ask the owner to try: home, "Video mới" (then archive that project), the project page, pause/resume, a Claude box message.
  - Record the verdict and requested changes in the ledger. Apply changes inside this plan's scope; everything else goes to the matching later plan.
- [ ] **Step 4: Commit** `docs: Studio README, HANDOFF and CLAUDE.md for the long-form workflow`.
