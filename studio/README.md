# Studio

Studio is the owner's dashboard for long-form history videos. It shows the "🔔 Cần bạn" inbox and the projects, has a project page with a step bar and a language strip, and a bottom bar with the job list and a Claude box.

## Start and stop

```
.venv/bin/python -m studio            # prints: Studio: http://127.0.0.1:8765
```

Stop it with Ctrl+C. Running jobs are killed with the process. On the next start they are marked `interrupted` and listed in "Cần bạn". They never rerun on their own.

The port and the lanes are set in `config/studio.json`:

```
"lanes": {"claude": 1, "agy": 4, "render": 1, "cpu": 2}
```

A lane is the maximum number of jobs of that sort running at once.

## Where state lives

| What | File |
|---|---|
| Inbox | `studio/state/inbox.json` (cross-process lock: CLI tools may add items while Studio runs) |
| Jobs | `studio/state/jobs/<id>.json` + `<id>.log` |
| Pause | `studio/state/pause.json`. Pause lets running jobs finish and starts nothing new. |
| Claude box | `projects/<id>/.studio/session` + `claude.jsonl`, or `studio/state/claude-general/` when no project is open |
| Step bar / language strip | `project.json` keys `steps` and `lang_status` |

All of these are gitignored except `project.json`.

## Job kinds

| Kind | Lane | Module | What it does |
|---|---|---|---|
| `claude` | claude | `claude_box` | The Claude box (one session per project) |
| `agy_research`, `agy_draft`, `agy_chat` | agy | `workers`, `chat` | Research sources, write the Vietnamese draft, chat edits |
| `claude_verify`, `claude_review` | claude | `workers` | Check facts against quotes, review the Vietnamese script |
| `agy_shotlist`, `agy_image`, `agy_image_review` | agy | `workers`, `image_worker` | Shot list, image generation, image review |
| `agy_rewrite` | agy | `langscript` | Native rewrite of one language from the beat outline (no Vietnamese sentences) |
| `claude_review_lang` | claude | `langscript` | Review one language; clean → auto-approve, flags → "Cần bạn" with back-translation |
| `timing_build` | cpu | Plan 5 `timing` | Sentence timing from the voice parts (queued by `voice.drop` when all parts are in) |
| `agy_upload_texts` | agy | `upload` | Title, description (one sources line, no links), tags |
| `render_thumb` | render | `thumb` | Thumbnail still (Remotion `Thumb`) → `lang/<code>/upload/thumb.png` |

## For later plans

Add a job kind:

```python
from tools.longform import jobs
jobs.register(jobs.Kind("agy_image", "agy", build=lambda p: [...argv...], on_end=lambda job: ...))
```

`build` validates the params and returns argv. It runs at enqueue time, so bad input fails in the HTTP call. Then add a route in `studio/server.py` that calls `jobs.enqueue("agy_image", params, project_id, label)`.

Ask the owner something:

```python
from tools.longform import inbox
inbox.add("001-bach-dang", "image_review", "BG08 được 3/5, chờ bạn duyệt", screen="images", key="img:BG08")
inbox.resolve_key("img:BG08")   # when it is settled
```

The same open `key` updates the item instead of repeating it. A new item goes to Telegram with a link to the screen.

Move a step:

```python
progress.set_step(pdir, "images", "wait")
progress.set_lang(pdir, "en", "voice", "done")
```

The states are `todo|doing|wait|done`.

## Security model

- The server binds `127.0.0.1` only. Never `0.0.0.0`.
- Every request must carry Studio's own `Host`, which blocks DNS rebinding.
- Every POST must be `application/json`, and, when an `Origin` is sent, Studio's own origin. Other web pages therefore cannot start jobs.
- The browser never sends a command. It names a job kind; the kind builds the argv.
- The Claude box runs `claude -p` with `--permission-mode acceptEdits` and the `allowed_tools` list from `config/studio.json`. Never `--dangerously-skip-permissions`. A message that starts with `-` gets a leading space, so the CLI cannot read it as a flag.
- Remote access (from a phone outside the house) is not built. If it is added later, it goes through Tailscale plus a password, never an open port.
