# HANDOFF: long-form history video workspace

Written 2026-10-31 for any agent (Claude Code or Gemini through `agy`) that picks this work up.
Read this, then `CLAUDE.md` (workspace rules and folder map), then the spec. The Shorts-era handoff is archived at
`/Users/quoctung/Documents/AI/archive/2026-10-31/workspace-code/HANDOFF-shorts-era.md`.

Workspace root: `/Users/quoctung/Documents/AI/youtube-skills-workspace`. It is a git repo on branch `main`, with remote
`https://github.com/tungnq2606/longform-workflow` (public). Make a branch before you change anything, and do not push
unless the owner asks.

## 1. The owner

- Vietnamese. **Reply in Vietnamese**, short and plain. Code, file names and commands stay in English.
- Runs the channel "Công Trường Lịch Sử" alone on one Mac. Pays for a Claude subscription (Claude Code, `claude -p`,
  no API key) and Google AI Ultra (Gemini through `agy`).
- Standing rule, said many times: **never invent or state anything false**: numbers, people, causes, sources.
- Makes the voices by hand on the web: Vbee for Vietnamese, ElevenLabs for the other languages. Uploads to YouTube by hand.

## 2. What the workflow makes

One long video (10–15 min) of Vietnamese history in simple 2D, exported in several languages from the same scenes.
The first set is vi (source), en, ja, de and es. Each language goes to its own YouTube channel, but the workflow only
knows projects and languages, not channels. The proposed first topic is Mông–Nguyên / the Bạch Đằng stakes, 1288.
The owner has not confirmed it yet.

- Spec (approved): `docs/superpowers/specs/2026-10-31-longform-workflow-design.md` (Vietnamese)
- Roadmap (6 plans): `docs/superpowers/plans/2026-10-31-longform-roadmap.md`

## 3. Who does what (owner's decision, 2026-10-31)

| Work | Who |
|---|---|
| Find sources, write the first script draft | agy (Gemini) |
| Review the script: facts against sources, content, storyteller voice | Claude |
| Every image: generate, review, redo (no gflow/Flow, ever) | agy |
| Remotion scenes and assembly | Claude |
| Other languages: rewritten natively per language from the fact bank and the beat outline, never translated line by line | agy, with a localization skill |
| Voices, upload, final yes/no | owner |

## 4. Look and animation (locked: `library/style/longform_v1.json`, approved 2026-10-31)

- AI draws the backgrounds (no people, no text) and the important characters. Characters are big-head cartoons about
  4 heads tall, drawn on chroma green `#00B140` and cut out by `tools/longform/cutout.py` into a kit
  (`library/characters/<id>/kit.json`).
- Crowds are stick soldiers drawn in code (`tools/anim/src/longform/Crowd.tsx`).
- Remotion does all motion, text and maps. Motion stays simple: no lip sync.
- Images are upscaled with Real-ESRGAN `realesr-animevideov3` (`tools/longform/upscale.py`; the binary sits in the
  gitignored `tools/upscale/vendor/`).
- Output: 2560x1440, 30 fps, ~16 Mbps H.264.
- The 10-second spike project is archived in `archive/2026-10-31/test-projects/000-spike/`; its approved assets stay in `library/`. Trần Hưng Đạo's kit height is 530 px in a 1440p frame.

## 5. Studio (Plan 2)

Start it with `.venv/bin/python -m studio`, then open http://127.0.0.1:8765. Details are in `studio/README.md`.

- Home page: the "🔔 Cần bạn" inbox, the projects, and "Video mới".
- Project page: the step bar, the language strip, and the project's inbox.
- Bottom bar: jobs (with stop and log) and the Claude box (one session per project).
- Screens: Kịch bản (Plan 3), Hình ảnh (Plan 4), Cảnh (Plan 5), Ngôn ngữ (Plan 6: tabs per language, script, voice,
  render, upload + thumbnail).
- Later plans add job kinds (`jobs.register`), inbox items (`inbox.add`) and step states (`progress.set_step`).
- Telegram: `tools/notify.py`. The secret is in `config/secrets/telegram.json`; never print or commit it.

## 6. Done and next

| Plan | State |
|---|---|
| 1 Foundation + spike | built, merged |
| 2 Studio shell | built |
| 3 Script chat + fact bank | built (branch `longform-plan3`). agy drafts; Claude reviews; every factual sentence links to a verbatim quote |
| 4 Images + streaming review | built (branch `longform-plan3`). agy for every image; reviews in parallel; lessons in `library/lessons/` |
| 5 Scene board + production Remotion | built in a parallel worktree; timing, scenes, `Longform`, `render_lang`, `Cards.tsx` |
| 6 Languages + voice + upload | built in its own worktree: native rewrite per language, checks + Claude review, voice drop-in, upload texts, thumbnails |

Merge notes for Plans 5 + 6: Plan 6 enqueues Plan 5's `timing_build` by name and its render button posts to Plan 5's
`/api/projects/<id>/render/<lang>`; `jabreak.lines` (Plan 6) still has to be passed to Plan 5's `Cards.tsx` for ja.

Each plan is written in detail only when it starts (superpowers writing-plans → executing-plans, with the ledger in
`.superpowers/sdd/<plan>/`).

## 7. Per video, step by step (what the owner does)

1. **Đề tài**: measure demand with `tools/research/scout.py`; "Video mới" in Studio (title + languages).
2. **Kịch bản** (chat screen): ask agy to research; Claude checks every fact against its quote; ask agy for a draft;
   Claude reviews it. Fix red sentences, decide yellow ones, then "Chốt kịch bản".
3. **Hình ảnh**: agy writes the shot list and draws; each image is reviewed as soon as it exists. Approve the 3/5
   images, redo or reject the rest; new hero poses go into the kit.
4. **Cảnh**: Claude writes the beat-keyed scene file; check the previews on the scene board.
5. **Ngôn ngữ** (per language tab): "Viết lại (agy)" → code checks → Claude review runs by itself. A clean language
   is approved automatically; otherwise read the flags in "Cần bạn" (each with a Vietnamese back-translation) and
   "Chốt" or ask for a new rewrite/review. Glossary rows are proposals until confirmed.
6. **Giọng**: "Chuẩn bị phần giọng", copy each part into Vbee (vi) or ElevenLabs (others, paid plan), save as the
   shown `NN.mp3`, drop all files on the tab. When every part is there, timing runs by itself.
7. **Render**: press Render for the language (Plan 5); the final 1440p MP4, `.srt` and chapters land in `lang/<code>/render/`.
8. **Upload**: "Viết text upload (agy)", "Tạo thumbnail" (approved background + hero pose + title), copy title,
   description (one sources line, no links) and tags; on YouTube set altered/synthetic content = Yes. Never add an
   "AI illustration" line.

## 8. Rules you must not break

All of `CLAUDE.md`, and in particular:

- No invented facts. When the records disagree, say both in plain words.
- No source names spoken in the voice-over.
- No text inside AI images.
- Move, never delete. Archive lives in `/Users/quoctung/Documents/AI/archive/2026-10-31/`.
- Studio stays on 127.0.0.1. Never use `--dangerously-skip-permissions`.
- No new macOS-only dependencies, no new `.sh` scripts.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` when Claude makes them.
