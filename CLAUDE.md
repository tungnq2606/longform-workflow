# Long-form history video workspace

One workflow only: long (10–15 min) 2D history videos, Vietnamese source script, exported in several languages
(vi, en, ja, de, es for now). Shorts and the old channels (The Median Worker, Fossil Receipts, horror) were
archived on 2026-10-31 to `/Users/quoctung/Documents/AI/archive/2026-10-31/` (moved, not deleted). The workflow
does not manage YouTube channels: a project produces one render per language; the owner uploads.
The owner talks to Claude in Vietnamese.

- Design (approved 2026-10-31): `docs/superpowers/specs/2026-10-31-longform-workflow-design.md`
- Roadmap (6 plans): `docs/superpowers/plans/2026-10-31-longform-roadmap.md`
- Plans built: 1 (foundation + spike), 2 (Studio shell), 3 (script chat + fact bank), 4 (images), 5 (scenes + Remotion),
  6 (languages + voice + upload); plans in `docs/superpowers/plans/2026-10-31-plan*.md`. State and merge notes: `HANDOFF.md` §6
- Handoff for another agent: `HANDOFF.md`

## Folder map

```
projects/NNN-slug/          one video: project.json, research/, script/, images/, scenes/, audio/
  lang/<code>/              per language: script/ (script.json, check.json), audio/ (parts.json, parts/NN.txt + NN.mp3),
                            timing.json, render/, upload/ (upload.md, upload.json, thumb.png)
library/                    shared by every video: characters/ (hero kits), crowds/, backgrounds/, style/,
                            glossary/<lang>.json (names + readings, seeds checked:false), stylebook/<lang>.json,
                            localization/GUIDE.md (agy rewrite guide), lessons/, research/
config/languages.json       voice engine, speed, font, line breaking per language
config/studio.json          Studio port, job lanes, Claude box permissions (acceptEdits + allowed tools)
config/secrets/             Telegram secret (gitignored: never print or commit)
studio/                     Studio dashboard: server.py (API), static/ (UI); runtime state in studio/state/ (gitignored)
tools/longform/             Python package for the new workflow (stdlib + Pillow, unittest)
tools/anim/                 Remotion project; new long-form components in src/longform/
tools/imageprompts/         older prompt builder and style files (reference for the prompt standard)
tools/research/scout.py     YouTube demand/competition measurement (yt-dlp)
tools/kit/storyboard.py     sentence timing from audio pauses (reused later)
tools/edge-tts-batch/       Edge extension for batch ElevenLabs voice
tools/notify.py             Telegram: send(text), link(project, screen) (secret in config/secrets/telegram.json)
library/lessons/            prompt_lessons.json (MUST block of every image prompt), LESSONS.md; library/research/ scout
                            data (moved from channels/vn-history/ in Plan 4); channel brand is in
                            /Users/quoctung/Documents/AI/brand/cong-truong-lich-su/
```

Python: `.venv/bin/python` (Pillow 11.3.0). Tests: `.venv/bin/python -m unittest discover -s tools/longform/tests -v`,
`node --test studio/static/` and `cd tools/anim && node --test src/longform/ && npx tsc --noEmit -p .`.
Start Studio: `.venv/bin/python -m studio`, then open http://127.0.0.1:8765 (localhost only; see `studio/README.md`).

## Languages (Plan 6)

- Other languages are **rewritten** natively by agy (`agy_rewrite`) from the beat outline (goal + fact claims and
  quotes), the glossary, the language style book and the guide; agy never gets the Vietnamese sentences. Same beat ids;
  each beat may use only the facts the source script used in that beat (else red).
- `lang_check` (code, `langscript.check` → `check.json`), then `claude_review_lang` (Claude): clean → approved
  automatically; flags → "Cần bạn" with a Vietnamese back-translation.
- Voice by hand on the web: `voice.prepare` writes part texts (Vbee ≤ ~55 s, ElevenLabs ≤ 4,500 chars, a sentence is
  never split); dropping all `NN.mp3` queues Plan 5's `timing_build`.
- `agy_upload_texts` (title, description with one sources line, tags; chapters from the timing) and `render_thumb`
  (Remotion `Thumb`, Noto Sans JP + `jabreak.ts` kinsoku for ja).

## Rules (do not break)

- Never invent facts, numbers, people or causes. Every factual sentence traces to a source with a verbatim quote;
  legends say "tương truyền", debated points say "có ý kiến cho rằng", archaeology "cho thấy", never "chứng minh".
- Voice-over never reads modern citations (authors, papers, museums, URLs). Exception: when historical records
  disagree, say both in plain words ("sử nhà Trần chép…, còn sử nhà Nguyên lại ghi…"). The description has one short
  sources line, names only, no links. Never add "Video minh họa bằng AI…"; set altered/synthetic = Yes on upload.
- Voice: a history storyteller, light humour for young viewers, short sentences, light Vietnamese slang, no English
  slang, "bạn" (never "chúng ta" or "bạn nhỏ"), jokes never bend facts.
- AI images: no text, no letters. Backgrounds have no people. Hero images on flat chroma green `#00B140`.
  Crowds are code-drawn in Remotion. All on-screen text and maps come from Remotion.
- Output 2560x1440, 30 fps, ~16 Mbps H.264, AAC 48 kHz; keep only the final file per language.
- Licences: ElevenLabs voice from a paid plan for monetised videos; music and SFX licensed for monetised YouTube;
  OFL fonts; no third-party images or clips (not even as AI references); Remotion free licence ≤3 employees.
- Review: Gemini scores 1–5. 4–5 passes; 3 waits for the owner; 1–2 is redone with the review's fix, at most twice,
  then waits for the owner. Anything on the prompt's MUST NOT list caps the score at 3.
- Prompts are structured specs (shot, angle, layout, setting, people, props with sizes against the body, light,
  must_not); no vague words (some, a few, several, dramatic, cinematic). Every prompt gets the MUST block of lessons.
- Work queues live on disk; pause finishes the running step and starts nothing new; reviews and lessons never block.
- No new macOS-only dependencies (use Pillow, not `sips`; Python, not new `.sh`).
