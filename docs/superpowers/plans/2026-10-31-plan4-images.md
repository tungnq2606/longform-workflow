# Plan 4: Images + streaming review — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill Studio's "Hình ảnh" tab and "Thư viện" screen. agy turns the approved script into an image list, generates every background, prop and hero pose, and reviews each image as soon as it exists, several in parallel. Images that pass are upscaled to YouTube quality. The owner approves or redoes images from a keyboard-driven review grid. Approved hero poses join the character kit.

**Architecture:**
- Images are items in `projects/<id>/images/items.json`. Each item moves through a small state machine driven by jobs on the agy lane:
  - `agy_image`: generate, then machine check, then upscale;
  - `agy_image_review`: score 1–5 with a per-type rubric, then pass / wait for the owner / automatic redo.
- `agy_shotlist` (agy) proposes items from the approved script.
- Prompts are structured specs rendered with the `longform_v1` style lock plus the MUST block of lessons.
- Lessons move from `channels/vn-history/` to `library/lessons/`.
- agy always runs as agy itself (a Python worker that calls the agy CLI). It never goes through Claude, never runs shell commands or MCP tools, and never uses skip-permissions.

**Tech Stack:** Python 3.9 + Pillow; existing modules `imagegen.generate` (agy `generate_image`), `upscale.upscale` (Real-ESRGAN `realesr-animevideov3`), `cutout.cut/check`, `kit.add_image/write_ts`, Plan 2 `jobs`, `inbox`, `progress`, Plan 3 `script`, `agy`; vanilla JS.

**Spec:** `docs/superpowers/specs/2026-10-31-longform-workflow-design.md` §3, §4.5, §4.9 (binding) · previous plans 1–3 (interfaces) · Mockup `.superpowers/brainstorm/34991-1793441859/content/layout-v2.html` §3–4

## Global Constraints

- All constraints of Plans 2–3 hold.
- **Review rule (spec §3):**
  - Score 4–5 passes.
  - Score 3 waits for the owner (inbox item `image_review`).
  - Score 1–2 is redone with the review's fix, at most 2 times, then waits for the owner.
  - Anything on the item's MUST NOT list caps the score at 3.
- **AI images:** no text, no letters.
  - Backgrounds have no people and include a ground line or path.
  - Hero poses are drawn on flat chroma green `#00B140`, cartoon about 4 heads tall, full body, portrait aspect, and **one figure only** (forbid sheet layouts; lesson from Plan 1).
  - AI never draws a hero into a background.
- **Prompt standard:** structured spec fields `shot, angle, layout, setting, people, props (sizes against the body), light, must_not`. No vague words (`some, a few, several, dramatic, cinematic`): the spec validator rejects them. Every prompt gets the MUST block of matching lessons (at most 8 rules).
- **Quality (owner):** backgrounds are upscaled to `upscale.BG_SIZE` (2816x1584) and heroes x2. An image whose upscaled size is short of that fails the machine check.
- **Parallel:** each image is reviewed as soon as it is generated; nothing waits for a batch. The agy lane limit (`config/studio.json` lanes.agy, default 4) can be changed from the Images tab, capped at 8.
- Review problems are shown in Vietnamese.
- Tests: `.venv/bin/python -m unittest discover -s tools/longform/tests -v`, `node --test studio/static/`, `cd tools/anim && node --test src/longform/ && npx tsc --noEmit -p .`
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **agy returns a background with a person or text, or a hero sheet with 3 figures.**
   - The background review scores it ≤ 3 because of its MUST NOT list, and it never auto-passes.
   - A hero with more than one figure fails the machine check (a cutout component count above 1) before review (Task 3, `test_multi_figure_hero_fails_check`).
2. **Two images finish at the same time.** Both are reviewed at once, and `items.json` keeps both updates (lock) (Task 2, `test_concurrent_item_updates`).
3. **A redo loop.**
   - Score 2, then a redo, score 2, a redo, score 2: the item waits for the owner after 2 redos and never loops a third time (Task 4, `test_redo_capped_at_two`).
4. **The owner approves a hero pose whose cutout touches the edge or keeps green.** Approval is refused with the `cutout.check` problems shown (Task 6, `test_approve_pose_runs_cutout_check`).
5. **agy quota runs out mid-batch.**
   - `QuotaExhausted` pauses Studio (`jobs.set_paused(True, "agy hết quota")`) and adds an inbox item.
   - The item goes back to `queued`, not `failed` (Task 3, `test_quota_pauses_and_requeues`).

---

### Task 1: Lessons in the library + structured image specs

**Files:**
- Move: `channels/vn-history/prompt_lessons.json` → `library/lessons/prompt_lessons.json`; `channels/vn-history/LESSONS.md` → `library/lessons/LESSONS.md`; `channels/vn-history/research/` → `library/research/`
- Move (archive, Shorts-only): `tools/gemini/` → `<archive>/workspace-code/tools/gemini/`, with a README line
- Create: `tools/longform/lessons.py`, `tools/longform/imgspec.py`
- Test: `tools/longform/tests/test_imgspec.py`

**Interfaces:**
- Produces:
  - `lessons.path() -> str` (`<library>/lessons/prompt_lessons.json`).
  - `lessons.rules_for(text: str, target="image", limit=8) -> list[str]`: rules whose `when` keywords occur in the text (case-insensitive), or that have no keywords; most frequent first.
  - `lessons.add(problems: list[str], example: str) -> None`: appends each problem as a new lesson `{id, target: "image", when: [], rule, count: 1, examples: [example], added}`, deduplicated by normalised rule text (a match raises `count`). No AI merge in this plan.
  - `imgspec.TYPES = ("bg", "prop", "pose")`.
  - `imgspec.FIELDS = ("shot", "angle", "layout", "setting", "people", "props", "light", "must_not")`.
  - `imgspec.VAGUE = ("some", "a few", "several", "dramatic", "cinematic", "epic", "beautiful")`.
  - `imgspec.validate(spec: dict, kind: str) -> list[str]`: Vietnamese problems.
    - It reports missing fields (`people` may be the literal `"none"` for bg), vague words, `must_not` that is not a list, and a bg whose `people` is not `"none"`.
  - `imgspec.render(spec: dict, kind: str) -> str`:
    - the style-lock block (`background` or `character` text from `library/style/longform_v1.json`);
    - the spec fields as `Field: value` lines;
    - `MUST NOT:` the item's list plus the style lock `negative`;
    - `MUST:` lesson rules from `lessons.rules_for`.
    - For a pose it adds: "Exactly one figure. Full body, feet visible. Plain flat chroma green #00B140 background. Portrait framing."
- [ ] **Step 1: Write failing tests:**
  - `test_validate_missing_and_vague`
  - `test_bg_people_must_be_none`
  - `test_render_includes_style_and_must`
  - `test_pose_render_single_figure`
  - `test_lessons_rules_for_keyword`
  - `test_lessons_add_dedupes`
- [ ] **Steps 2–4:** Run (FAIL), implement, run (PASS).
- [ ] **Step 5:** Run `grep -rn "channels/vn-history\|tools/gemini" --include=*.py --include=*.md tools studio CLAUDE.md HANDOFF.md`. Fix every hit to the new paths. Commit `feat: library lessons and structured image specs; archive Shorts-era gemini tools`.

---

### Task 2: Image items store (state machine, lock)

**Files:**
- Create: `tools/longform/images.py`
- Test: `tools/longform/tests/test_images.py`

**Interfaces:**
- Produces:
  - `images.STATES = ("queued", "generating", "reviewing", "pass", "wait", "approved", "rejected", "failed")`.
  - Item (`images/items.json`, a list):
    - Fields: `{"id": "BG01|P01|H01", "type": "bg|prop|pose", "beat": "B03"|null, "kit": "tran-hung-dao"|null, "pose_key": "point.determined"|null, "spec": {...}, "prompt", "refs": [paths], "state", "attempts": int, "files": {"raw", "final", "cutout"}, "score": int|null, "problems": [str], "fix": str, "history": [{"at", "event", "score", "note"}], "reuse": "library background id"|null}`.
  - `images.load(pdir) -> list[dict]`.
  - `images.add(pdir, type, spec, beat=None, kit=None, pose_key=None, reuse=None) -> dict`:
    - ids `BG01…`, `P01…`, `H01…` per type;
    - validates the spec with `imgspec`;
    - renders the prompt;
    - state is `queued`, or `approved` when `reuse` names an existing library background.
  - `images.update(pdir, item_id, **fields) -> dict`:
    - runs under an `fcntl` lock on `images/.lock`;
    - appends a history event when `state` changes;
    - an unknown id raises `KeyError`.
  - `images.counts(pdir) -> {state: n}`.
  - Every state change also calls `progress.set_step(pdir, "images", ...)`:
    - `doing` while any item is queued, generating or reviewing;
    - `wait` when any item is in `wait` and none are running;
    - `done` when every item is `approved` or `rejected`.
- [ ] **Step 1: Write failing tests:**
  - `test_add_ids_per_type`
  - `test_add_validates_spec`
  - `test_update_history`
  - `test_concurrent_item_updates`: 8 threads update different items; all 8 updates persist.
  - `test_step_follows_states`
  - `test_reuse_library_background_approved`
- [ ] **Steps 2–4:** Run (FAIL), implement, run (PASS). **Step 5:** Commit `feat: image item store with locked state machine`.

---

### Task 3: Generation worker (agy) + machine check + upscale

**Files:**
- Create: `tools/longform/image_worker.py` (CLI `python -m tools.longform.image_worker generate|review <project> <item>`)
- Modify: `tools/longform/workers.py` (register kinds)
- Test: `tools/longform/tests/test_image_worker.py`

**Interfaces:**
- Consumes: `imagegen.generate`, `imagegen.QuotaExhausted`, `upscale.upscale`, `cutout.cut/check`, `images.update`, `jobs`.
- Produces:
  - Job kind `agy_image`:
    - lane `agy`; params `{"project", "item"}`;
    - argv `[venv python, "-m", "tools.longform.image_worker", "generate", pid, item]`;
    - cwd `WS`.
  - `image_worker.generate_item(pdir, item_id) -> dict`. It does, in order:
    1. Sets state `generating`.
    2. Calls `imagegen.generate(prompt + fix, refs, images/raw, item_id, aspect)`, where aspect is `"16:9"` for bg/prop and `"9:16"` for a pose.
    3. Runs the machine check (`check_raw`).
    4. Upscales:
       - bg: `upscale(raw, images/final/<id>.png, size=BG_SIZE)`;
       - pose: x2, then `cutout.cut` into `images/final/<id>.png`;
       - prop: x2.
    5. Sets state `reviewing` and enqueues `agy_image_review`.
  - `image_worker.check_raw(item, path) -> list[str]` (Vietnamese problems):
    - the image is smaller than 1024 px on its long side;
    - an exact duplicate (same SHA-256) of another item's raw file;
    - for a pose: no transparency after a trial cutout, the figure touches the edge, or **more than one figure**, meaning more than one connected opaque component larger than 2% of the opaque area (Pillow + flood fill on a 256 px thumbnail).
  - On problems the item goes back to `queued` with `attempts += 1` and `fix` set to the problems (English, for the prompt), until attempts reach 3. After that the state is `wait` with an inbox item.
  - On `QuotaExhausted`: `jobs.set_paused(True, "agy hết quota")`; an inbox item `quota` ("agy hết lượt tạo ảnh; Studio đã tạm dừng"); the item returns to `queued`; the worker exits 0.
- [ ] **Step 1: Write failing tests.** Patch `imagegen.generate` to copy a fixture image, and patch `upscale.upscale` to resize with Pillow.
  - `test_generate_bg_goes_to_review`
  - `test_pose_cutout_and_portrait_aspect`
  - `test_multi_figure_hero_fails_check`
  - `test_duplicate_fails_check`
  - `test_quota_pauses_and_requeues`
  - `test_argv_runs_python_worker_not_claude`
- [ ] **Steps 2–4:** Run (FAIL), implement, run (PASS). **Step 5:** Commit `feat: agy image generation worker with machine check and upscale`.

---

### Task 4: Review worker (agy) + rubric + redo rule + lessons

**Files:**
- Modify: `tools/longform/image_worker.py`
- Create: `tools/longform/prompts/image_review.md`
- Test: `tools/longform/tests/test_image_review.py`

**Interfaces:**
- Produces:
  - Job kind `agy_image_review`, lane `agy`, argv `[venv python, "-m", "tools.longform.image_worker", "review", pid, item]`.
  - `image_worker.RUBRIC = {"bg": [...], "prop": [...], "pose": [...]}`. Short English check lines:
    - bg: no people or animals; no text; style lock; a ground line or path; the period is right.
    - pose: matches the kit model sheet (face, costume colours, proportions); the requested pose; one figure; clean edges.
    - prop: the object as specified; no text; style.
  - `image_worker.review_item(pdir, item_id) -> dict`. It asks agy (via `agy.argv`, cwd a run folder holding a copy of the final image and of the refs) to read the image and write `review.json` `{"score": 1-5, "problems": [vi], "must_not_hits": [str], "fix": "English prompt fix"}`. Then:
    - any `must_not_hits` caps the score at 3;
    - 4–5: state `pass`;
    - 3: state `wait`, plus inbox `image_review` "<id> được 3/5: <problems>" (key `img:<pid>:<id>`, screen `images`);
    - 1–2 with `attempts < 2`: `attempts += 1`, `fix` set, state `queued`, enqueue `agy_image` again;
    - 1–2 with `attempts >= 2`: state `wait` plus inbox;
    - every score ≤ 3 calls `lessons.add(problems, "<pid>/<id>")`;
    - a missing or bad `review.json`: state `wait` with problem "agy không chấm được ảnh này".
  - `pass` is not `approved`: the owner approves in the grid (A). **[ruling allowed]** A setting `auto_approve_pass` in `config/studio.json` (default false) may approve passes automatically.
- [ ] **Step 1: Write failing tests.** Use a fake agy writing a `review.json` fixture.
  - `test_score_5_passes`
  - `test_score_3_waits_with_inbox`
  - `test_score_2_redoes`
  - `test_redo_capped_at_two`
  - `test_must_not_caps_score`
  - `test_bad_review_waits`
  - `test_low_score_adds_lesson`
- [ ] **Steps 2–4:** Run (FAIL), implement, run (PASS). **Step 5:** Commit `feat: agy image review with rubric, redo rule and lessons`.

---

### Task 5: Shot list from the approved script (agy)

**Files:**
- Create: `tools/longform/prompts/shotlist.md`
- Modify: `tools/longform/workers.py`
- Test: `tools/longform/tests/test_shotlist.py`

**Interfaces:**
- Produces:
  - Job kind `agy_shotlist`, lane `agy`, params `{"project"}`. `build` refuses unless `script.load(pdir)["approved"]` is true.
  - Run folder:
    - the approved script;
    - `library_index.summary()` (reusable backgrounds and kits with their poses);
    - the style lock;
    - the spec field rules.
  - agy writes `result.json`: `{"items": [{"type", "beat", "spec", "kit", "pose_key", "reuse"}]}`.
  - Rules in the prompt:
    - one background per beat unless a library background fits (`reuse`);
    - props only when a sentence needs an object seen close;
    - heroes only from existing kits, with a new `pose_key` only when no kit pose fits;
    - crowds are never images (Remotion draws them).
  - `on_end`:
    - every item goes through `images.add`; a spec error refuses the whole list with an inbox item;
    - then one `agy_image` job per queued item;
    - `progress.set_step(images, "doing")`.
- [ ] **Step 1: Write failing tests:**
  - `test_requires_approved_script`
  - `test_items_added_and_jobs_queued`
  - `test_bad_spec_refuses_all`
  - `test_reuse_background_not_generated`
- [ ] **Steps 2–4:** Run (FAIL), implement, run (PASS). **Step 5:** Commit `feat: agy shot list from the approved script`.

---

### Task 6: Owner actions, kit poses, cast sheet

**Files:**
- Create: `tools/longform/castsheet.py`
- Modify: `tools/longform/images.py`, `studio/server.py`
- Test: `tools/longform/tests/test_image_actions.py`, plus new cases in `test_server.py`

**Interfaces:**
- Produces:
  - `images.approve(pdir, item_id) -> dict`:
    - bg/prop: state `approved`.
    - pose: runs `cutout.check(final, source=raw)`. Problems raise `ValueError` (Vietnamese). Otherwise it calls `kit.add_image(kit, pose_key, raw_upscaled)`, then `kit.write_ts()`, then state `approved`.
    - It resolves the inbox key `img:<pid>:<id>`.
  - `images.redo(pdir, item_id, note) -> dict`: `fix` = the note, attempts unchanged, state `queued`, enqueue `agy_image`.
  - `images.reject(pdir, item_id)`.
  - `images.save_background(pdir, item_id, name) -> str`: copies an approved bg into `library/backgrounds/<slug>.png` with an empty `.json` geometry stub `{"horizonY": null, "groundY": null, "path": []}` for Plan 5.
  - `castsheet.build(pdir) -> str`: every approved pose of the project's kits, laid out in a row on white, labelled by pose key (Pillow text). Saved as `images/cast_sheet.png`. It never sends anything to AI.
  - API:
    - `GET /api/projects/<id>/images` → `{"items", "counts", "lanes"}`;
    - `GET /api/projects/<id>/images/<item>/<raw|final>` → the image file (looked up from the item, never from a path);
    - `POST …/images/<item>/approve|redo|reject` (redo `{"note"}`);
    - `POST …/images/approve_many` `{"ids"}`;
    - `POST …/shotlist`;
    - `POST /api/lanes` `{"agy": n}`: 1–8, updates the runner live and saves the config;
    - `POST …/images/<item>/to_library` `{"name"}`;
    - `GET /api/library/kits` (`kit.json`s with pose keys and thumbnails via `/api/thumb`);
    - `POST /api/library/kits/<kit>/new_pose` `{"pose_key", "spec", "project"}`: adds a pose item with the model sheet and stand image as refs.
- [ ] **Step 1: Write failing tests:**
  - `test_approve_bg`
  - `test_approve_pose_runs_cutout_check`
  - `test_approve_pose_adds_to_kit`
  - `test_redo_requeues_with_note`
  - `test_cast_sheet_composed_locally`
  - `test_image_file_route_only_known_items`
  - `test_lanes_endpoint_caps`
- [ ] **Steps 2–4:** Run (FAIL), implement, run (PASS). **Step 5:** Commit `feat: image approve/redo/reject, kit poses, cast sheet, images API`.

---

### Task 7: Review grid UI + library screen

**Files:**
- Create: `studio/static/images_view.js`, `studio/static/library_view.js`
- Modify: `studio/static/app.js`, `lib.js`, `style.css`, `lib.test.js`

**Interfaces:**
- `lib.js` helpers (tested):
  - `imageStateLabel(state)` (Vietnamese);
  - `scoreClass(score)`;
  - `nextIndex(i, n, key)` for ←/→ with wrap;
  - `needsOwner(item)` (state `wait`).
- **Images tab** (`#/p/<id>/images`), mounted like the script screen (own poll every 3 s, never interrupts typing):
  - Top bar:
    - counts per state;
    - "Lập danh sách ảnh" (shot list);
    - the agy lane control (− n +);
    - filter chips "Tất cả / Cần bạn / Đang làm / Đã duyệt".
  - **Grid:**
    - a card per item: thumbnail, or a placeholder with a spinner while queued, generating or reviewing;
    - the id, a score badge and the state;
    - cards appear and update as each image finishes.
  - **Large view** (click a card):
    - the image;
    - the spec;
    - problems (Vietnamese) and history.
  - Keys:
    - `A` approves;
    - `R` asks for a note and redoes;
    - `X` rejects;
    - `←/→` move between images;
    - `Esc` closes.
  - Shift-click selects several cards; "Duyệt N ảnh" calls `approve_many`.
  - "Đưa vào thư viện" on an approved background.
  - "Ảnh tổng nhân vật" opens the cast sheet.
- **Library screen** (`#/library`):
  - Kits: a card per character with its pose thumbnails and "+ Tư thế mới" (form: pose key, pose description, project).
  - Backgrounds: thumbnail grid.
  - Crowds: the factions from `tools/anim/src/longform/factions.ts`, as a read-only list served by a small API that parses the file.
  - Style lock status.
- [ ] **Step 1:** Write failing helper tests. **Step 2:** Run (FAIL).
- [ ] **Step 3:** Implement. **Step 4:** Run (PASS).
- [ ] **Step 5:** Screenshot in light and dark (headless Chrome, 1500 px and 500 px) with a fixture root on port 8799, as in Plan 3. Fix what looks broken.
- [ ] **Step 6: Commit** `feat: Studio image review grid and library screen`.
