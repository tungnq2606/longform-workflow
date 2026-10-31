# YouTube production workspace (several faceless channels)

Handoff for another agent (Gemini/agy): read `HANDOFF.md` (full project state, rules, tools, open work).

Faceless US channels with clothed stick-figure visuals; English videos; the owner talks to Claude in Vietnamese.
Each channel lives in its own folder under `channels/`; tools, templates and the dashboard are shared.

| Channel | Folder | About |
|---|---|---|
| The Median Worker (@TheMedianWorker) | `channels/median-worker/` | data-sourced explainers on everyday money (rent vs pay, cost of living, money traps); strategy docs in `docs/` |
| Fossil Receipts (@FossilReceipts) | `channels/fossil-receipts/` | evidence-first explainers on how prehistoric and ancient humans survived |

New channel: copy `templates/channel/` to `channels/<id>/` and follow its README (channel.json, style, setup, brand).

## Folder map

```
channels/<id>/         one folder per channel:
  channel.json           id, name, handle, about, language, image style; the dashboard lists every channel.json
  CHANNEL_SETUP.md       Studio texts and settings; STYLE.md (median-worker only: old drawn style)
  brand/                 avatar, banner, watermark + brand.py (fossil-receipts: art prompts in brand/images/)
  research/              channel-level research: topic scout runs, Gemini phrase ideas, niche notes
  videos/NNN-slug/       one folder per video (layout below)
  docs/                  strategy and niche documents (median-worker)
LICENSES.md            licences for fonts, voice, music, Remotion, images (all channels)
tools/kit/             drawing library: build_visuals.py (text, shapes, render via headless Edge, font),
                       storyboard.py, scene_kit.py, props.py, fonts/ (Patrick Hand, SIL OFL)
tools/pipeline/        voice_text.py, frames.py, review.py, project.py, build.sh, new_video.sh CHANNEL NNN slug
tools/editor/          render.swift + render (AVFoundation MP4 renderer), editor.html (timeline preview)
tools/anim/            Remotion toolkit: animated scenes (anim/scenes.tsx) and image videos (Frames), render.sh, render_frames.sh
tools/edge-tts-batch/  Edge extension that batch-generates ElevenLabs audio from voiceover_tts/*.txt
tools/imageprompts/    image styles (style/<id>.json, one per look) + cast/shot JSON -> image prompts + validator (README.md)
tools/gemini/          agy_images.py (generate), agy_review.py (check), agy_thumb.py: Gemini via the Antigravity CLI
tools/research/        scout.py (YouTube demand/competition measurement with yt-dlp)
dashboard/             Studio dashboard (dashboard/start.sh -> http://127.0.0.1:8765): all steps + Claude box, see dashboard/README.md
templates/video/       skeleton for a new video; templates/channel/ skeleton for a new channel
```

In the rest of this file, VIDEO means `channels/<id>/videos/NNN-slug`.

Inside VIDEO:
```
VIDEO.md                 status checklist (update it as steps finish)
research/                brief-outline.md, sources_log.csv, sim/, script_versions/
script/script.txt        source of truth: one paragraph per voice block, [src: ...] tag per paragraph
script/pronounce.json    TTS spelling fixes, e.g. {"HUD": "H-U-D"}
script/voiceover_tts/    generated text to paste into the TTS tool (NN.txt)
audio/NN.mp3             voice files (one per block)
visuals/scenes.py        the scenes: S[block] = [(sentence_no, fraction, svg_body), ...], BG, CHAPTERS, DESC_CHAPTERS
visuals/frames_1440p/    generated frames (2560x1440, channel standard); export/review.html for review
packaging/               titles, briefs, thumbs.py, thumbs/
render/                  project.json (1440p), subtitles.srt, editor.html, NNN-slug_1440p.mp4 (keep only the final video)
upload/                  upload.txt (title, description, tags, settings), description.txt, thumbnail.png
```

## Pipeline (one video)

| # | Step | How |
|---|---|---|
| 1 | Topic + angle | skill `yt-topic-scout` |
| 2 | Title, promise, thumbnail briefs | skill `yt-packaging` |
| 3 | Brief, outline, sources | skill `yt-script-retention`; every number goes in `research/sources_log.csv` |
| 4 | Script | `script/script.txt`; one simulation pass + fact audit per `yt-script-retention/references/sim-protocol.md`; stop after one pass |
| 5 | Voice text | `python3 tools/pipeline/voice_text.py VIDEO` then owner generates `audio/NN.mp3` (ElevenLabs, extension in tools/edge-tts-batch) |
| 6 | Scenes | ANIMATED (standard): write `anim/scenes.tsx` (pattern: video 001). Static fallback: `visuals/scenes.py` |
| 7 | Build | Animated: `tools/anim/render.sh VIDEO` (block test: add block number; live preview: `studio`). Subtitles/chapters: run `tools/pipeline/build.sh` once or frames.py + project.py. Static: `tools/pipeline/build.sh VIDEO`: 1440p frames timed to the audio, review page, project.json, subtitles, chapters into upload texts, 1440p MP4 (add `1080` only if a 1080p copy is asked for) |
| 8 | Review | open `visuals/export/review.html`; owner pastes notes; fix scenes; rebuild |
| 9 | Thumbnail | `packaging/thumbs.py` (copy from 001), 1280x720, test at 200 px |
| 10 | Upload | `upload/upload.txt`; settings in `channels/<id>/CHANNEL_SETUP.md`. The owner uploads and schedules in YouTube Studio (an API upload tool was removed 2026-10-24: unaudited API projects lock uploads as private) |

New video: dashboard "Video mới" or `tools/pipeline/new_video.sh <channel-id> 002 short-slug`, then follow VIDEO.md.
Timing only (voice changed, scenes not): `python3 tools/pipeline/frames.py V && python3 tools/pipeline/project.py V`, then render.
Render alone (old static videos): `cd VIDEO/render && ../../../../../tools/editor/render project.json` (test: `--max 20`).

## Rules (do not break)

- Median Worker video 001 (channels/median-worker/videos/001-rent-vs-pay) is published and closed (old animated style). Never edit, re-render or redo it; use it only as a format reference. The workflow starts new videos only. Videos with "Status: published" in VIDEO.md are closed the same way.

- Sources (owner, 2026-10-23): the voice-over never names or cites sources (no "according to the Bureau of Labor Statistics", no study or museum names read aloud); [src: ...] tags stay in script/script.txt only for checking and are stripped from the voice text. The description lists sources in one short block, names only, no links (e.g. "Sources: BLS Usual Weekly Earnings (Q2 2026); Census ACS 2024"). research/sources_log.csv keeps the full URLs.

- Character images: never hand-write a character prompt. Fill images/cast.json + images/shots.json and run tools/imageprompts/make_prompts.py, so the channel's image style (channel.json "style": median-worker stickman-v1, fossil-receipts stickman-v2 = prehistoric look with hair, dirt, stronger expressions) STYLE block is in every prompt and every script gets one cast and pose sheet (all characters, all poses), composed from the model sheets. Never attach or quote the third-party reference sheet.
- Key images (route "manual": one model sheet per character in scenes, animals too; first scene; shots with "key": true) are made in Google Flow with Nano Banana Pro through gflow-cli by agy_images.py itself (since 2026-10-28; `--no-flow` leaves them to the owner); all other scenes go through agy. Both pass the review rule below. The final thumbnail is still picked by the owner.
- The cast sheet is never generated by any AI: agy_images.py pastes the approved model sheets into refs/cast_sheet.png when the last one is approved (dashboard button "Ghép lại"). make_prompts.py refuses a character without a model sheet or with a used pose missing from its sheet_poses. Mark opening and climax shots "key": true when writing shots.json.

- Never invent numbers, people or causes. Every spoken figure has a source row; unverified items are marked on screen.
- No financial advice; explain mechanisms. The stick figure is labelled an illustration when it stands for a statistic.
- Hook: finding in the first sentence plus an open loop; no fake puzzles; reveal the loop later in the video.
- Length standard 5-8 minutes (target ~6); length comes from sourced beats, never filler.
- Spoken figures are rounded; exact figures go on screen. Max ~4 spoken figures per paragraph.
- Visual style v2: each beat is a small scene where the character acts with objects; little text; ground line; tint per section; Patrick Hand font only (licence). See channels/median-worker/STYLE.md.
- Vary structure between videos (YouTube "inauthentic content" policy: no templated mass production).
- Licences: voice must come from a paid ElevenLabs plan for monetised videos; music only with a licence allowing monetised YouTube; no third-party images or clips. See LICENSES.md.
- Output is ALWAYS 1440p (2560x1440, ~16 Mbps H.264, AAC 48 kHz) per the owner; keep only the final video file in render/.
- Upload: "not made for kids", altered/synthetic content = Yes (AI voice), Unlisted first.

## Gotchas

- Telegram: `tools/notify.py` (`notify.send(text)`, no-op until `dashboard/secrets/telegram.json` has token + chat_id; never print or commit that file). auto_images.py and flow_clips.py send their summaries (items waiting for approval, gflow stops); the dashboard sends failed jobs and finished renders/reviews.
- Fewer retries (owner, 2026-10-28): every prompt sent to agy/Flow gets a MUST block = the channel's lessons (`channels/<id>/prompt_lessons.json`, written by `tools/gemini/lessons.py learn VIDEO` from review problems after each image/clip run) + Gemini's pre-flight fixes for that exact prompt (`tools/gemini/preflight.py`, run before each generation round, stored in `images/runs/preflight.json`). Prompt files themselves stay as make_prompts wrote them. Long-form scenes attach only the model sheets of the characters in the shot (cast sheet only when they do not fit); Shorts attach the channel's approved `style_swatch` (`tools/shorts/style_swatch.py`) instead of old video frames once channel.json sets it. Dashboard shows tries per image/clip and first-try pass rate. Shorts shots.json can tune the channel style per video: top-level "style_lock" (replaces the style block), "negative", "veo_tail" (rules appended to every Veo prompt) and a per-shot "sound" line (vn-history 003 is the example; its images/build_shots.py lists the Bạch Đằng lessons behind them).
- Prompt standard (owner, 2026-10-29: "chuẩn hóa prompt tối ưu nhất, chi tiết nhất"): Shorts shots describe images as a structured "spec" (shot, angle, top/middle/bottom layout, setting, people with who/where/pose/hands/gaze/wear, props with what/size/where/state, light, must_not), edits as "edit" (keep/change/must_not) and clips as "motion" (camera, mover, action, speed, end, still). `make_shorts_prompts.py --check` refuses missing fields and vague words (some, a few, several, dramatic, cinematic...). Example: vn-history 003 `images/shot_specs.py`. Flow sends the manifest's clip prompt (motion + veo_tail + sound), also after a Gemini rewrite.
- Queue (owner, 2026-10-28): owner actions only write to the per-video queue on disk (`tools/workqueue.py`: auto.json, image_queue.json, flow_decisions.json); the dashboard reconciler (every 30 s) starts the missing runner. "⏸ Tạm dừng" finishes the step in progress and starts nothing new; a failed or stopped run pauses automation until "▶ Tiếp tục".
- Review rule (owner, 2026-10-28) for every generated image and Veo clip: Gemini 4-5/5 passes (lowered from 5 on 2026-10-29); 3 waits for the owner (dashboard "Cần bạn duyệt"); 1-2 is redone automatically with the review's fix, at most 2 times, then waits for the owner. Images: `tools/gemini/auto_images.py VIDEO` (generate, review, redo); owner approvals in `images/runs/approvals.json` (per file mtime).
- One button (owner, 2026-10-28: "chỉ cần duyệt và tạo"): `tools/shorts/auto_video.py VIDEO` = auto_images.py then flow_clips.py; dashboard "▶ Tạo tự động: ảnh + clip". Unreviewed start images are reviewed automatically; approving an image starts its clip; decisions made during a run are queued in `images/runs/flow_decisions.json` and picked up by the running job. A clip Flow may have billed but gflow lost (exit 9 after submit) is never re-submitted automatically: it waits for the owner. Clip shape: every shot is first-frame-only unless shots.json sets "end_frame" (shot id or path): use that only for a small, local end state, never for big global changes (those are separate shots joined by a dissolve).
- Shorts lessons: read `channels/vn-history/LESSONS.md` before planning a new Short (numbers and reasons per video; prompt rules also live in the channel's prompt_lessons.json). Credits per video: `tools/shorts/credit_report.py channels/<id>` (flow_clips.py logs the Flow balance before and after each clip since 2026-10-30). veo-fast starts from the prompt that passed at veo-lite (`flow_clips.py` `override()`); wide multi-chamber cutaways and liquid above an opening are planned as stills or tiny local motion. `make_shorts_prompts.py --check` refuses (unless the shot sets "allow_motion": "<reason>"): motion on a cutaway with liquid, motion on a close-up of a patterned surface, sizes in mm/cm, more than 4 active shots ("max_active" raises it); it adds liquid and fire rules to those clips. veo-fast stops after 2 failures when a passing veo-lite clip exists. The image review scores at most 3 when anything from the prompt's MUST NOT list is visible.
- Veo clips (Shorts): `tools/shorts/flow_clips.py VIDEO` drives Google Flow through gflow-cli 0.90.0 (unofficial; pinned, audited 2026-10-28, run with `GFLOW_CLI_UPDATE_CHECK=0`; never `gflow update` without re-auditing). Per shot: veo-lite test -> review -> (active shots only) veo-fast -> review -> Flow 1080p upscale; ambient shots keep the 5/5 veo-lite clip (gflow cannot do 4K video). Start image must score 4-5 or be owner-approved. One Flow call at a time with 30-75 s pauses (owner wanted speed, 2026-10-29); Gemini reviews each clip on a side thread while Flow makes the next one; stops at the first gflow failure. Lessons are merged in the background (`lessons.learn_in_background`, log in images/runs/lessons.log), so a pause or a run never waits for them. State in `images/runs/flow_state.json`. Login once: `gflow auth login --browser chrome`. gflow needs a visible (headed) Chrome; macOS pulls off-screen windows back, so `dashboard/config.json` "gflow"."window_position" parks it on the second display (hiding Chrome made downloads fail more often). A clip whose download misses gflow's 20 s grace is fetched again for free (`gflow data download`).
- Frame rendering opens headless Edge per frame (~2 s each); a full 1440p build (frames + render) takes about 5-6 min.
- Sentence timing is found from pauses in the audio; if a frame changes on the wrong sentence, check `visuals/timeline.csv`.
- Swift build warnings in render.swift are expected; the binary works.
- Census direct pages/API often fail from tools; Census Reporter API works for ACS tables. FRED `.txt` data pages work via WebFetch.
