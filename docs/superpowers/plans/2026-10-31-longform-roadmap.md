# Long-form workflow: roadmap

**Spec:** `docs/superpowers/specs/2026-10-31-longform-workflow-design.md` (approved by the owner 2026-10-31).

The spec covers six subsystems. Each gets its own plan, written in detail only when the previous one is done,
because later plans depend on what the spike (Plan 1) decides about style, kit format and staging.
Each plan ends with working, testable software.

| # | Plan | Delivers | Depends on |
|---|---|---|---|
| 1 | Foundation + 10-second spike (`2026-10-31-plan1-foundation-spike.md`) | git + venv, Shorts/office/legacy code archived, `projects/` + `library/` + `config/languages.json`, cutout tool, image-gen wrapper, Remotion crowd + hero components, rendered 10 s spike the owner approves; style lock `longform_v1` | — |
| 2 | Studio shell | New dashboard (`studio/`): home with "🔔 Cần bạn" inbox, project list, "Video mới", project page with step bar and language strip, job bar + Claude box (subscription, `claude -p`), disk-backed queue, pause/resume, Telegram. Old `dashboard/` archived (secrets move to `config/secrets/`); `HANDOFF.md` rewritten for the new workflow; `channels/vn-history/brand/` moved out of the workflow. | 1 |
| 3 | Script chat + fact bank | Chat screen (3 columns), fact bank storage (URL or uploaded file + page, verbatim quote, saved page text, grade A/B/C, status), Claude research/writing turns, Gemini independent check, sentence→fact links, red/yellow gate, conflicting-records rule, storyteller style book with self-learning rules per language | 2 |
| 4 | Images + streaming review | Background/prop/hero-pose generation from structured specs + style lock + MUST lessons; per-image pipeline (generate → machine check → Gemini review → auto redo) with N parallel workers; per-type rubrics; review grid with keyboard (A/R/←/→, multi-select); library screen (kits, crowds, reusable backgrounds, new pose from model sheet); per-script cast/pose sheet composed from approved images | 2 (3 for prompts from script) |
| 5 | Scene board + production Remotion | Scene board (sentence → background, characters, motion, sound, status, preview), scenes file keyed by sentence, map component (Natural Earth coastlines, arrows, labels, "modern map" note), two-source card, chapter titles, music by chapter with ducking, SFX cues (AI-suggested, owner-edited), sentence timing from pauses, 1440p render per language, subtitles, chapters | 1, 4 |
| 6 | Languages + voice + upload | Language tabs (source beside translation), Claude translation 1:1 with per-language style book, glossary + pronunciation tables, automatic checks (sentence count, numbers, names, no new sentences) + Gemini second check + back-translation for warnings, voice text split per tool limits as "Cần bạn" tasks, mp3 drop-in and completeness check, Japanese font + line breaking, per-language thumbnail (code-drawn text), title/description/tags/sources line | 3, 5 |

Rules that carry across all plans: spec section 3 (1440p, no invented facts, sources not spoken except conflicting
records, licences, review thresholds 4–5 pass / 3 owner / 1–2 auto-redo ×2, prompt standard, disk queue, nothing blocks,
Telegram), every image through agy (no gflow/Flow, owner 2026-10-31), and no new macOS-only dependencies (use Pillow, not `sips`; Python, not new `.sh`).
