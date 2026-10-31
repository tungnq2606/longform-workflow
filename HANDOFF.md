# HANDOFF: YouTube production workspace (written 2026-10-24 for Gemini / Antigravity CLI `agy`)

Claude's session quota is nearly used up, so you (Gemini through `agy`) continue. This file is the whole picture: what the project is, who the owner is,
what exists, what is half-done, and the rules you must not break. Read it fully before you change anything.
Also read `CLAUDE.md` (workspace rules) and `dashboard/README.md`. Everything below was checked against the files on 2026-10-24; where something is
unverified it says so.

**Update 2026-10-30 (Shorts, Công Trường Lịch Sử):** before planning or prompting a vn-history Short, read `channels/vn-history/LESSONS.md` (numbers, credit table, design rules for the next video) and the Shorts bullets in `CLAUDE.md` Gotchas. `tools/shorts/make_shorts_prompts.py --check` now refuses the shot shapes that broke before.

Workspace root: `/Users/quoctung/Documents/AI/youtube-skills-workspace` (not a git repository, so there is no history to roll back to: copy a file
before you rewrite it).

---------------------------------------------------------------------------------------------------

## 1. The owner and how to talk to them

- The owner is Vietnamese. **Reply in Vietnamese.** Keep search phrases, titles, quotes, code, commands and file paths in English.
- The channels are for **US audiences**, so all published text (scripts, titles, descriptions, tags, channel texts) is English (US spelling).
- The owner runs everything alone, on one Mac (macOS, zsh), on a Claude Team plan (Claude Code) and a Google AI Ultra plan (Gemini, Antigravity, Flow).
- Standing constraint, said many times: **"tranh bịa hoặc làm nội dung sai sự thật"**: never invent numbers, people, causes, sources or results.
  If you did not check something, say so. Report outcomes faithfully (failed = failed).
- Output of channel videos is **always 1440p** (2560x1440, about 16 Mbps H.264, AAC 48 kHz); keep only the final MP4 in `render/`.
- The owner does not want to be asked many questions. Pick a sensible default, say what you picked, and continue.

## 2. What the project is

Two faceless YouTube channels with **clothed stick-figure illustrations** (style id `stickman-v1`; Fossil Receipts uses `stickman-v2` since 2026-10-24: hair, dirt, stronger expressions), AI voice-over (ElevenLabs), videos assembled by
Remotion. One shared toolchain, one local dashboard, one folder per channel:

| Channel | Folder | About | Status |
|---|---|---|---|
| The Median Worker (@TheMedianWorker) | `channels/median-worker/` | data-sourced explainers on everyday money (rent vs pay, cost of living) | video 001 is **published and closed** |
| Fossil Receipts (@FossilReceipts) | `channels/fossil-receipts/` | evidence-first explainers on how prehistoric and ancient humans survived | channel name chosen 2026-10-23; YouTube channel **not created yet** (owner action) |

Closed means: never edit, re-render or redo Median Worker video 001. Any video whose `VIDEO.md` has a line `Status: published` is closed the same way.
The workflow only starts **new** videos.

## 3. Folder map (current layout, after the 2026-10-23 cleanup)

```
HANDOFF.md, CLAUDE.md, README.md, LICENSES.md
channels/<id>/
    channel.json            id, name, handle, about, language, style ("stickman-v1"), status; the dashboard lists every channel.json
    CHANNEL_SETUP.md        texts and settings for YouTube Studio (fossil-receipts is complete; median-worker has the older version)
    brand/                  avatar_800.png, banner_2560x1440.png, watermark_150.png, brand.py (fossil-receipts: brand/images/ = cast.json, shots.json, prompts, frames)
    research/               channel-level research: scout/ (yt-dlp measurements), gemini/ (phrase ideas, topic research), niche notes
    videos/NNN-slug/        one folder per video, layout in section 5
    docs/                   (median-worker) strategy and niche research .docx/.html
templates/video/            skeleton for a new video;  templates/channel/ skeleton for a new channel (README.md says how)
tools/
    kit/                    drawing library for the old static videos (Edge-rendered SVG frames), font Patrick Hand (SIL OFL)
    pipeline/               voice_text.py, frames.py, review.py, project.py, build.sh, new_video.sh CHANNEL NNN slug
    editor/                 render.swift + render (AVFoundation renderer for old static videos)
    anim/                   Remotion 4.0.537 project: compositions "Video" (animated scenes) and "Frames" (generated images); render.sh, render_frames.sh
    edge-tts-batch/         Edge browser extension: batch ElevenLabs text-to-speech from voiceover_tts/*.txt into ~/Downloads/tts/
    imageprompts/           image style files + cast/shot JSON -> image prompts + validator (README.md, tests/)
    gemini/                 agy_images.py (generate), agy_review.py (check), agy_thumb.py, croptop (Swift crop helper)
    research/               scout.py (YouTube demand and competition measurement with yt-dlp)
dashboard/                  local Studio dashboard (section 8) + the 3D office (section 12)
```

The Claude skills (`yt-topic-scout`, `yt-packaging`, `yt-script-retention`, `yt-video-pipeline`) live in `/Users/quoctung/Documents/AI/.claude/skills/`.
Claude's memory notes are in `~/.claude/projects/-Users-quoctung-Documents-AI/memory/` (the facts in them are repeated here).

## 4. The rules (do not break; the owner set all of these)

1. **Sources are never spoken.** The voice-over never names a source (no "according to the BLS", no museum, journal or study name read aloud).
   `[src: ...]` tags stay in `script/script.txt` for checking and are stripped from the voice text. The video **description** has one short block
   `Sources: Name (year); Name (year)`: names only, no links, no URLs. Full URLs live in `research/sources_log.csv`.
2. **Never hand-write a character image prompt.** Fill `images/cast.json` and `images/shots.json`, then run `tools/imageprompts/make_prompts.py VIDEO`.
   It pastes the locked STYLE block of `stickman-v1` word for word into every prompt, adds one cast-and-pose sheet with **all characters and all poses of
   the script**, and its validator refuses prompts that break the style. Never edit `style/stickman_v1.json` (add `stickman_v2.json` for a new look).
3. **Never attach or quote the third-party reference sheet** (`tools/imageprompts/style/reference/third_party_reference_sheet.png`). It is only for studying the look.
4. **Key images are made by the owner in Google Flow (Nano Banana Pro)**: one model sheet per character that appears in scenes (animals too), the first
   scene, shots with `"key": true`, the final thumbnail. **The cast sheet is never generated** (Flow, Gemini or agy): `agy_images.py` pastes the approved
   model sheets together into `refs/cast_sheet.png` as soon as the last one is approved (since 2026-10-25: Flow redrew characters off-model). Everything else goes through `agy` automatically. Mark the opening and climax shots `"key": true` when writing `shots.json`.
5. **No invented facts.** Every spoken figure has a row in `research/sources_log.csv`. Spoken figures are rounded; exact figures go on screen.
   Interpretation or hypothesis must be labelled on screen ("interpretation", "hypothesis", "debated", "not confirmed by DNA").
6. **No financial advice** (Median Worker); explain mechanisms. The stick figure is labelled an illustration when it stands for a statistic.
7. Hook = the finding in the first sentence plus an open loop that is revealed later. Length standard 5-8 minutes (channel 2 may run 8-12 when sourced
   beats support it). Length comes from sourced beats, never filler. Vary structure between videos (YouTube "inauthentic content" policy).
8. Licences: monetised videos need a paid ElevenLabs plan; music only with a licence that allows monetised YouTube; no third-party images or clips;
   font Patrick Hand only (see `LICENSES.md`). Upload defaults: "not made for kids", altered or synthetic content = Yes (AI voice), Unlisted first.
9. **Do not publish, upload, email, post or share anything** and **do not delete videos or folders** unless the owner explicitly asks.
   The owner does uploads (and scheduling, in YouTube Studio) and deletions by hand. Do not build API upload tools:
   videos uploaded through an unaudited API project are locked as private (removed 2026-10-24).
10. The dashboard binds to `127.0.0.1` only; keep it that way.
11. Do not break the old dashboard. The 3D office is decoration only (see section 12).

## 5. One video: folder layout and the 10 steps

```
VIDEO.md                 status checklist (can be stale; the dashboard computes the real state from the files)
research/                topic.md, gemini/*.md (Gemini drafts), brief-outline.md, sources_log.csv, sim/, script_versions/ (backups)
script/script.txt        source of truth: one paragraph per voice block, blank line between blocks, [src: ...] tag per paragraph
script/pronounce.json    TTS spelling fixes, e.g. {"HUD": "H-U-D"}
script/voiceover_tts/    NN.txt generated text to paste into the TTS tool (one per block)
audio/NN.mp3             voice files (one per block), imported from ~/Downloads/tts/
images/                  cast.json, shots.json, prompts/ (NNN_id.txt, manifest.json, prompts.md), raw/ (every variant), refs/ (approved sheets),
                         frames/ (2560x1440 PNG scenes), runs/ (state.json, review.json, log.jsonl), frames_timeline.json
render/                  <slug>_1440p.mp4 (keep only the final), subtitles.srt
packaging/  upload/      titles, thumbnails, upload.txt (=== TITLE ===, === DESCRIPTION ===, === TAGS ===, === UPLOAD SETTINGS ===)
.dashboard/              Claude session id and chat history for this video (dashboard files)
```

Steps shown by the dashboard (`steps(d)` in `server.py`): 1 research, 2 script, 3 viewer simulation (optional), 4 shots (cast, shots, prompts),
5 sheets (model sheets + cast sheet, approved), 6 scenes (every scene image), 7 image review (optional), 8 voice (mp3 per block), 9 render, 10 upload texts.

## 6. Who does what (routing, to save Claude's quota)

| Work | Who |
|---|---|
| Measure search phrases (views, freshness, small channels) | `tools/research/scout.py` (yt-dlp), no AI |
| Suggest phrases, topic research, source gathering, competitor analysis, viewer simulation, title and tag drafts | **Gemini (agy)**; answers saved under `research/gemini/` |
| Generate every non-key image; review every image; thumbnail drafts | **Gemini (agy)**: `agy_images.py`, `agy_review.py`, `agy_thumb.py` |
| Write scripts and accept facts, cast/shots JSON and prompts, fixes, render setup, upload texts | Claude (the dashboard "Gửi Claude" box and `CLAUDE_TASKS`) |
| Validation, timing, upscaling, render, subtitles, chapters | plain code |
| Key images in Flow, voice generation in ElevenLabs, YouTube uploads, final decisions | **the owner** |

Gemini text is a draft: facts it gives must be checked against the source URL before they go into a script.
Now that Claude's quota is nearly gone, you may be asked to do Claude's jobs too (script writing, shots, upload texts). If you do, follow the same rules
and the prompts in `CLAUDE_TASKS` (`dashboard/server.py`), and **verify every fact with its source URL**.

## 7. Tools reference

### `tools/imageprompts/make_prompts.py VIDEO [--check]`
Reads `images/cast.json` and `images/shots.json`, writes `images/prompts/`. Order of images: a model sheet per character used in scenes, one cast-and-pose
sheet, then scenes. `route` is `manual` for model sheets, the first scene and `"key": true` shots, `compose` for the cast sheet (pasted from the model
sheets, never generated), otherwise `agy`. `check_refs` refuses a character in scenes without `"model_sheet": true` or with a used pose missing from its
`sheet_poses` (max 8). `check_refs` runs before building and `check()` validates
every prompt (forbidden words, limits: max 3 reference images, max 4 named characters per scene, 6000 characters). Styles live in `tools/imageprompts/style/<id with _>.json`; the video's style is `cast.json "style"`, default from `channel.json`.
Tests: `python3 -m unittest discover -s tools/imageprompts/tests` (12 tests, passing on 2026-10-25).

### `tools/gemini/agy_images.py VIDEO [options]`
Generates through the Antigravity CLI. Options: `--only ID,ID`, `--redo ID`, `--approve ID [--variant N]` (sheets must be approved, everything after a sheet
waits for it), `--import ID FILE` (owner's Flow image; refused for the cast sheet), `--compose` (rebuild the cast sheet from the approved model sheets; also runs by
itself after every model-sheet approval, via `tools/imageprompts/compose_cast_sheet.py`), `--include-manual`, `--status`, `--workers N` (parallel, default 3-4; scheduler waits for dependencies).
Saves every variant in `images/raw/`, checks size and ratio, converts scenes to 2560x1440 PNG in `images/frames/`. `images/runs/state.json` is written with a
**per-item merge under a cross-process file lock** (`state.json.lock`): several runs may write at once. Scenes attach `refs/cast_sheet_figures.png` (for a composed sheet: each person's
model sheet cut above its expression row) so the model does not copy the labelled expression heads. A redo appends a CORRECTION from `review.json` when the image was
rejected by review. `agy_review.py VIDEO [--only ID,ID] [--all] [--workers N]` reviews in batches of 4 against the cast sheet and writes `images/runs/review.json`
(`ok`, `score` 1-5, `problems`, `fix`, file mtime). `agy_thumb.py VIDEO "concept" ["BIG TEXT"]` makes thumbnail candidates; the title text is drawn by code
(image models misspell), 1280x720 into `upload/thumbs/`.

### `tools/anim/` (Remotion)
`prep_frames.py` writes `images/frames_timeline.json`, `render/subtitles.srt` and `src/current_frames.ts` (points the project at one video). `render_frames.sh VIDEO`
renders composition "Frames" (generated images timed by sentence, Ken Burns zoom, crossfade, chapter cards) on port 3124; `render.sh VIDEO [block|studio]` renders
the animated-scenes composition "Video". GPU rendering uses `--gl=angle` (about 26x faster). Bitrate target 16M. Props must be JSON. Remotion's licence is free
only for individuals or companies with 3 or fewer employees.

### Other
`tools/pipeline/voice_text.py VIDEO` builds `script/voiceover_tts/NN.txt` and reports characters per block (ElevenLabs credits). `tools/research/scout.py FILE`
scores phrases (demand, fresh_top, fresh_rel, small_wins, score). `new_video.sh CHANNEL_ID NNN slug` or the dashboard "Video mới" creates a video folder.

## 8. The dashboard (`dashboard/`)

Run: `python3 dashboard/server.py` (or `dashboard/start.sh`), open http://127.0.0.1:8765. Python standard library only (`ThreadingHTTPServer`).
`index.html` is a single-page app (hash routes `#board`, `#topics`, `#v/<channel>/<slug>/<tab>`; tabs script, shots, voice, preview, upload) with the assistant dock at the bottom.
`config.json`: `extra_channels` (the "demo" examples), `claude` (permission mode `acceptEdits`, allowed tools), `gemini` (agy path, model `gemini-4-argon-high`, `workers` 4).
Channels now come from `channels/*/channel.json` (read on each request, so a new channel appears without a restart).

HTTP API: GET `/api/state` (channels, videos, next step, jobs), `/api/video?channel=&slug=` (detail), `/api/job?id=` (job + log tail), `/api/scout?channel=`,
`/api/text?path=`, `/file?path=` (Range support, path guard); POST `/api/action` (below), `/api/save`, `/api/upload` (voice, image, thumbnail);
`/office` serves the 3D office; `/vendor/...` and `/office/...` serve static files (path-guarded, nothing outside those folders).

POST `/api/action` actions: `prompts`, `check_prompts`, `generate` (workers), `redo`, `redo_many`, `approve`, `confirm`, `review`, `thumb`, `use_thumb`, `delete_script`
(backs up first), `open_tts`, `import_tts`, `voice_text`, `save_shot` (rolls back if validation fails), `claude_shot`, `render`, `open_render`, `studio`, `new_video`,
`scout`, `claude`, `gemini`, `suggest_phrases`, `stop`. Presets for Gemini: `research_topic`, `simulate`, `titles`, `competitors`.
A job is `{id, kind, label, video: "channel/slug", cmd, status: running|done|error|stopped, started, ended, code, log, action, item}`. Jobs live **in memory**
(lost on restart); logs stay in `dashboard/jobs/*.log` (kept on purpose, 632 KB).

Claude headless: `claude -p --output-format stream-json --verbose --permission-mode acceptEdits --allowedTools ... --session-id/--resume`, `--model`, `--effort`,
one resumable session per video. Gemini jobs: `agy -p <task> --model <m> --output-format json --print-timeout 1800s --dangerously-skip-permissions [--add-dir VIDEO]`
run in `dashboard/agy_work/` (its own git repo), answers saved by the server because headless agy cannot write files.

## 9. agy / Antigravity facts (learned the hard way)

- Binary `~/.local/bin/agy` 1.4.5. Models `gemini-4-argon-{high,medium,low}`, `gemini-3.8-flash-{high,medium,low}`. The owner's default and our choice: **gemini-4-argon-high**.
- Image tool `generate_image {Prompt, ImageName, AspectRatio, ImagePaths (max 3)}`: no size option, output **1376x768 JPEG**, saved to
  `~/.gemini/antigravity-cli/brain/<conversation_id>/<ImageName>_<ms>.jpg`; our runner finds and copies it. The `image-generator` subagent retries up to 3 times.
  The subagent once claimed to be "Imagen 3": do not trust self-reports about the model.
- `--mode auto` is not available on this account. In headless `-p` mode `write_file` is **denied**, so jobs return text and the server/runner writes files.
  Whether interactive agy can write files was not tested.
- `--dangerously-skip-permissions` is used only for text and review jobs inside `dashboard/agy_work` (agy's terminal sandbox stays on).
- `--json-schema` gives structured output (used by `agy_review.py`).
- A quota stop returns status "stopped" (not a crash). Image models copy the structure of input images: attach only the figures crop for scenes and thumbnails.
- Flow (labs.google/flow) forces a visible watermark in some countries (research note: Vietnam, except Ultra 20x). **Unverified for this owner**: check a key image before publishing.

## 10. Current state of the work

**Fossil Receipts, video 001 "How prehistoric humans survived"** (`channels/fossil-receipts/videos/001-prehistoric-survival/`)
- Script done (13 voice blocks), `research/sources_log.csv` and `brief-outline.md` exist. The hook is an interpretation ("survived by keeping their weakest alive"); keep the on-screen "interpretation" labels.
  `VIDEO.md` checklist is stale (says "script draft"); the real state is below. Update it when you touch the video.
- Images: 2 model sheets + cast sheet approved; 73 scene frames exist (71 done, 1 approved, 1 pending = **01-01**). 01-01 is a manual (Flow) image: the current
  `frames/001_01-01.png` is an agy variant (v2: correct black stick limbs; the hide wrap knot is on the character's right shoulder, which is what the ELDER card says).
  The owner should either press "Xác nhận ảnh này" or redo it in Flow. Manual images: `sheet_elder`, `sheet_shanidar`, `cast_sheet`, `01-01`, `11-04`, `13-04`.
- The last review (`images/runs/review.json`) still lists 14 images with `ok: false` (score 1-3): 01-02, 02-02, 02-03, 02-04, 04-06, 08-01, 11-05, 11-06, 11-07, 11-08,
  12-01, 12-03, 13-02, 13-05. Some may have been redone since (review matches by file mtime). Re-run `agy_review.py VIDEO` and look at the result before you claim anything.
- Voice: 13 mp3 files exist in `audio/`. A 1440p render `render/001-prehistoric-survival_1440p.mp4` exists (about 654 MB, 5:24, made 2026-10-23 16:30) with `subtitles.srt`.
- **Not done**: upload texts (`upload/` does not exist), thumbnail, YouTube channel creation, the human fact check of the 8 `CHECK` rows in `sources_log.csv`,
  script lint (`script_lint.py` was not run). A viewer-simulation note exists (`research/gemini/20261023_114717_simulate.md`); whether its changes were applied to the script was not checked.

**Fossil Receipts, video 002 "how ancient humans survived without medicine"**: folder created from topic scout (score 13.79); `research/topic.md` and one Gemini
research note exist; `script/script.txt` is still the 46-word template. Next step: write the script (Gemini draft + source checks, then the yt-script-retention rules).

**Median Worker**: video 001 published and closed. No other video is started. The dashboard shows its "next step" as "Chia cảnh" because it has no images: ignore it.

**Fossil Receipts channel branding** (`channels/fossil-receipts/brand/`): draft avatar, banner (with safe-area check) and watermark exist (art by agy, text drawn by
`brand.py`). The owner still has to create the YouTube channel with handle `@FossilReceipts` and upload these (texts to paste: `brand/channel_description.txt`,
`brand/channel_keywords.txt`, details in `CHANNEL_SETUP.md`). Better art can be made in Flow with `brand/images/prompts/003_avatar.txt` / `004_banner.txt`, saved over
`brand/images/frames/001_avatar.png` and `002_banner.png`, then `python3 channels/fossil-receipts/brand/brand.py`.
Competitor to watch: "Old Stick Life" (@OldStickLife), same stick-figure prehistory idea, very small.

## 11. Bugs found and fixed (do not reintroduce)

- A Claude "rewrite this shot" button took pasted review problem text as the goal and wrote the defect into the prompt. The prompt template now says the note may be a defect
  to avoid, and the validator forbids phrases like "white-filled", "thick white". Keep both.
- Parallel image runs overwrote each other's `state.json`. Fixed with a per-item merge and a file lock (also used by the dashboard "confirm" action).
- `check()` crashed on an unknown pose: `check_refs` now runs first. `sips --cropOffset` crops around the centre: use `tools/gemini/croptop` instead.
- Thumbnails once showed fabricated text ("$1000/MONTH") and misspellings: all surfaces must be blank and the title is drawn by code.
- Never write `sleep` chains in a harness shell; use `until` loops or background jobs. A render job hides its half-written MP4 from the dashboard until it ends.
- Claude Code auto-mode blocks `rm`, `mv` to Trash and `rm -rf`; the owner runs those themselves with `! command` in the Claude prompt.

## 12. In progress: the 3D office (`/office`) , decorative only

**Owner's request (2026-10-24)**, in their words, translated: turn the dashboard into "an office with departments and employees", seen from above in 3D,
where you can watch the work. They then asked for a **second, better version**:
- use the `taste-skill` rules (anti-slop: no AI-purple, no hand-rolled icons, no em-dashes or decorative dots in visible text, honour `prefers-reduced-motion`, dark and light mode);
- **no stick-figure characters** (the first version used them): design a different kind of character;
- a **bigger office** with **scenery outside** (ground, street, trees, sky) so it is not monotonous;
- **everything animated**: workers visibly working, and **when a job finishes the finished folder is carried to the next room**, etc.;
- **names of rooms and staff must not float as labels**; put them on doors, walls and desk plaques so it does not look odd;
- it is a toy for fun, but it must be **polished, like a 3D animation**;
- **do not break the old dashboard** (the office only reads data; the old `index.html` stays as it is, except one sidebar link "Văn phòng 3D");
- the owner asked Claude to split the work into several subagents (parallel pieces: scene/architecture, characters, animation, HUD and data wiring, outdoor scenery, QA).

**What exists now**
- `dashboard/office/index.html`: **version 1**, working. Simple orthographic top-down office, 7 rooms, 17 stick-figure staff, CSS2D floating labels, side panel, job feed.
  It reads `/api/state` every 1.5 s (jobs running) or 4 s and `/api/job?id=` for the selected worker's log. `_old_v1_office.html.bak` is the original copy (its add-on import
  paths are outdated; ignore it).
- Server routes added in `dashboard/server.py` (`/office`, `/office/...`, `/vendor/...`, path-guarded). Checked 2026-10-24: all return 200, `../` traversal returns 404.
- Vendored libraries (no CDN at runtime): `dashboard/vendor/three/three.module.min.js` (three.js **0.170.0**, MIT, `vendor/three/LICENSE`) and add-ons under
  `vendor/three/addons/` (controls/OrbitControls, renderers/CSS2DRenderer, postprocessing/{EffectComposer, RenderPass, ShaderPass, OutputPass, UnrealBloomPass, GTAOPass,
  SMAAPass, BokehPass}, shaders/*, geometries/RoundedBoxGeometry, utils/BufferGeometryUtils, environments/RoomEnvironment, math/{ImprovedNoise, SimplexNoise}, objects/Sky, lines/*).
  Import map: `"three": "/vendor/three/three.module.min.js"`, `"three/addons/": "/vendor/three/addons/"`.
- Font: **Be Vietnam Pro** (SIL OFL, Vietnamese glyphs) self-hosted in `dashboard/office/fonts/` (weights 400-800), declared in `dashboard/office/css/fonts.css`.
  Draw sign text into canvas textures only after `await document.fonts.load('700 48px "Be Vietnam Pro"')`.

**What does not exist yet**: version 2 (all of the list above). Nothing of it is built; only the libraries, fonts and routes are ready.

**Data to drive the animation** (read-only; do not add write actions)
- Jobs from `/api/state` -> `jobs[]`; map `job.action` (fallback `job.kind`) to a worker. The v1 table is `STAFF` in `office/index.html`
  (research: `research_topic, competitors, suggest_phrases, gemini`; scout: `scout`; script: `write_script, fix_script, simulate`; art: `make_shots, claude_shot, prompts,
  check_prompts, generate, redo, redo_many, review`; voice: `voice_text`; edit: `render, studio`; publish: `write_upload, titles, thumb`; assistant: `claude`).
  `generate` runs N workers (read `--workers N` in `job.cmd`): show N painters busy.
- Videos from `/api/state` -> `channels[].list[]`: `{slug, title, next, next_label, next_who, done_steps, total_steps, published, render}`. `next` is the step key
  (`research, script, sim, shots, sheets, scenes, review, voice, render, upload`); it decides which room holds the video folder. `next_who` containing "Bạn" means the owner must act.
- Handoff animation: when a job's status changes from `running` to `done`, carry that video's folder from the worker's room to the room of the new `next` step (compare
  `next` before and after the next poll). A finished `render` job (`kind: "render"`) should deliver the video (a tape or disc) to the publish room.
- Keep reduced-motion support and a pause when the tab is hidden (`document.hidden`); cap the pixel ratio at 2; dispose geometries and materials you remove.

**Design direction suggested (not yet agreed with the owner)**: "decorative 3D diorama office for a solo creator, polished toy-animation look, restrained palette, one accent".
Characters: chunky rounded mascots, **not** stick figures. For example a bean-shaped body with real clothes or a headset, big readable silhouette, different species per
worker type (Claude, Gemini, machine robots, the owner as a person in the owner's green), idle and working animation sets (typing, reading, stamping, thinking, carrying).
Names on door lintels, wall signs, desk nameplates and window glass (canvas or SDF textures), never as floating HTML labels. Outside: ground plane, street, trees,
parked cars, a river or hills, sky with a slow day/night cycle from the real clock, clouds, birds. Render with soft shadows, ambient occlusion, a little bloom, tilt-shift,
a vignette (post-processing add-ons are already vendored).

**QA for any change to the office**
1. `python3 -m py_compile dashboard/server.py`; restart the server; `curl` `/`, `/office`, `/api/state` must return 200 and `/` must be byte-identical in behaviour (old dashboard unchanged).
2. Screenshot with headless Edge (software WebGL):
   `EDGE=$(python3 -c "import sys; sys.path.insert(0,'tools/kit'); import build_visuals as b; print(b.EDGE)")`
   `"$EDGE" --headless=new --use-angle=swiftshader --enable-unsafe-swiftshader --hide-scrollbars --user-data-dir=<tmpdir> --window-size=1600,1000 --virtual-time-budget=6000 --screenshot=<out.png> http://127.0.0.1:8765/office`
   then look at the image (check Vietnamese diacritics render, nothing overlaps the side panel, signs are readable).
3. Trigger a harmless job (`POST /api/action {"action":"check_prompts","channel":"fossil-receipts","slug":"001-prehistoric-survival"}`) and check the worker animates and the bubble shows.

## 13. Next steps, in priority order

1. Ask the owner what they want first. Likely: (a) build the 3D office version 2, (b) finish Fossil Receipts video 001 (image fixes, upload texts, thumbnail, fact check), (c) write video 002's script.
2. Fossil Receipts 001: re-review images, fix the ones that are really wrong with "Tạo lại" / "Sửa theo góp ý" (never include manual images in a bulk fix), write
   `upload/upload.txt` (yt-packaging rules: title, description with ONE short names-only Sources line, chapters from `render/subtitles.srt`, tags), make a thumbnail,
   have the owner fact-check the 8 CHECK rows. Everything is **Unlisted first**; the owner uploads.
3. Fossil Receipts 002: script -> sources log -> shots -> sheets (owner in Flow) -> scenes -> voice -> render -> upload texts.
4. Tell the owner to create the `@FossilReceipts` channel and upload the brand files before the handle is taken.

## 14. How to start (suggested first message for agy, run inside the workspace)

> Read HANDOFF.md, CLAUDE.md and dashboard/README.md completely. Summarise to me in Vietnamese in 10 lines what you understood and what you will do first. Do not change any file until I answer.

Use `--add-dir` for the workspace if you run it headless, and remember: in headless mode agy cannot write files on this account.
