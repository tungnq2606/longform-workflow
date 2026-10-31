# Plan 6: Languages + voice + upload — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every project language a full product: agy **rewrites** the script natively per language from the fact bank and the beat outline (no translation of Vietnamese sentences), automatic checks plus a Claude review guard the facts, the owner's hand-made voice files drop in part by part, and Studio prepares the upload texts and a code-drawn thumbnail per language.

**Architecture:**
- **Script per language:** `lang/<code>/script/script.json`, same schema as the source script and the **same beat ids**. Sentence ids are free.
- **Language data:** a glossary + pronunciation table per language (`library/glossary/<code>.json`), and a style book per language (Plan 3 `stylebook`).
- **Writing guide:** a localization guide for agy (`library/localization/GUIDE.md`).
- **Jobs**, all through Plan 2's queue, Plan 3's guards and Plan 4–5's structures:
  - `agy_rewrite` (agy) writes the language script;
  - `lang_check` (code) runs the automatic checks;
  - `claude_review_lang` (Claude) reviews, and back-translates flagged sentences into Vietnamese for the owner;
  - voice parts are split per the tool limits; mp3 files are dropped in; Plan 5 `timing.build` and `render_lang` take over;
  - `agy_upload_texts` (agy) writes the upload texts;
  - `render_thumb` (render) draws the thumbnail.

**Tech Stack:** Python 3.9; Remotion (thumbnail composition, Japanese font + line breaking); Plans 2–5 modules.

**Spec:** `docs/superpowers/specs/2026-10-31-longform-workflow-design.md` §3, §4.7 (binding: rewrite, not translate; beat alignment; checks; voices by hand; fonts), §4.4 (fact rules apply to every language), §5 · Plans 1–5

## Global Constraints

- All constraints of Plans 2–5 hold.
- **No translation (owner, 2026-10-31).**
  - The `agy_rewrite` prompt gets each beat's goal, its fact ids **with their claims and quotes**, the glossary, the language style book and the guide. It does **not** get the Vietnamese sentences.
  - Each beat may use only the facts the source script used in that beat.
- **Automatic checks per language**: every beat present; no fact outside the beat's list; numbers present in the linked facts (Plan 3 `script.colour`, so the same red/yellow/green); glossary names consistent.
- **Approval:**
  - A language whose checks pass and whose Claude review flags nothing is approved automatically (spec §5).
  - Flagged sentences go to "Cần bạn" with a back-translation into Vietnamese for the owner to decide.
- **Voices are made by hand on the web** (Vbee vi, ElevenLabs others). Studio prepares the part texts and file names.
  - Vbee parts stay under ~55 s of speech (Vbee inserts a system sentence past ~1 min).
  - ElevenLabs parts stay ≤ 4,500 characters (works with `tools/edge-tts-batch`).
  - A sentence is never split across parts.
- **Fonts:** `Noto Sans JP` (OFL) for ja. Japanese lines break between characters, but never before closing punctuation (`、。」』）！？ー`) and never after opening punctuation (`「『（`).
- **Upload texts:**
  - title, description, tags, chapters;
  - the description has exactly one short sources line: source names only, no links, no modern citations spoken anywhere;
  - never the line "Video minh họa bằng AI…" (the owner sets altered/synthetic = Yes at upload).
- **agy and Claude:** agy runs as agy (never through Claude, no shell, no MCP, no skip-permissions). Claude workers stay inside their run folder.
- Tests: `.venv/bin/python -m unittest discover -s tools/longform/tests -v`, `node --test studio/static/`, `cd tools/anim && node --test src/longform/ && npx tsc --noEmit -p .`
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **agy's rewrite slips in a fact the beat did not use, or a number from nowhere.** `lang_check` marks the sentence red, and the language cannot be approved (Task 3, `test_fact_outside_beat_red`, `test_number_not_in_facts_red`).
2. **agy's rewrite drops or merges beats.** Refused whole with an inbox item; the old language script stays (Task 3, `test_missing_beat_refused`).
3. **A Vietnamese sentence longer than the Vbee limit.** It becomes its own part and is flagged "câu dài hơn giới hạn Vbee, cắt bằng tay". It is never split mid-sentence and never dropped (Task 4, `test_long_sentence_own_part_flagged`).
4. **The owner drops `03.mp3` for a 5-part language, or the wrong language.** Studio accepts files only for known part names of that language, shows which parts are missing, and does not start timing until all parts are present (Task 4, `test_drop_unknown_part_refused`, `test_timing_waits_for_all_parts`).
5. **Japanese title on the thumbnail.** No line starts with `、。」` and none ends with `「`; long titles shrink to fit two lines (Task 6, `jabreak.test.ts`).

---

### Task 1: Glossary + pronunciation tables

**Files:**
- Create: `tools/longform/glossary.py`, `library/glossary/{en,ja,de,es}.json`
- Test: `tools/longform/tests/test_glossary.py`

**Interfaces:**
- Produces:
  - Table format: `{"lang", "names": [{"vi": "Trần Hưng Đạo", "target": "Tran Hung Dao", "reading": "", "checked": false, "note": ""}], "terms": [...same shape...]}`.
  - Seed **names only**, `checked: false` (Claude review or the owner confirms them):
    - Trần Hưng Đạo; Bạch Đằng; Ô Mã Nhi; Thoát Hoan; Đại Việt; Vân Đồn; Thăng Long; Trần Khánh Dư; nhà Nguyên.
    - Romanised forms for en/de/es: Tran Hung Dao, Bach Dang River / Bach-Dang-Fluss / río Bach Dang, Omar, Toghon, Dai Viet, Van Don, Thang Long, Tran Khanh Du, Yuan dynasty / Yuan-Dynastie / dinastía Yuan.
    - Katakana for ja: チャン・フン・ダオ (spec), バクダン川, ウマル, トガン, ダイヴィエト (大越), ヴァンドン, タンロン, チャン・カイン・ズー, 元朝.
    - These are seeds to confirm, not facts. Claude review checks them against sources when they are used.
  - `glossary.load(lang) -> dict`.
  - `glossary.add(lang, vi, target, kind="names", reading="", checked=False)`: deduplicates by `vi`.
  - `glossary.expected(lang, vi_texts: list[str]) -> list[(vi, target)]`: the names whose `vi` form occurs in the given texts.
  - `glossary.check(lang, vi_texts, target_text) -> list[str]` (Vietnamese): each expected `target` missing from the target text, matched case-insensitively and NFC-normalised.
  - `glossary.confirm(lang, vi)`.
- [ ] Steps: failing tests (`test_seed_ja_tran_hung_dao`, `test_expected_and_check`, `test_add_dedupes`, `test_confirm`), then run, implement, run, commit `feat: per-language glossary and name readings`.

---

### Task 2: Localization guide + per-language style books

**Files:**
- Create: `library/localization/GUIDE.md`, `library/stylebook/{en,ja,de,es}.json`
- Test: `tools/longform/tests/test_stylebook.py` (new cases)

**Steps:**
- [ ] **Step 1: Look for an existing skill** before writing one (owner: "tìm skill có sẵn nếu có thì lấy còn không thì tự viết hoặc kết hợp").
  - Search `~/.claude/skills`, `~/.claude/plugins/cache/**/skills`, `~/.gemini/antigravity-cli/builtin` and `~/.gemini/**/skills` for names or descriptions containing `locali`, `translat`, `transcreat`.
  - Read what you find; use only content that fits.
  - Record what you searched and found in the guide's first lines ("Sources of this guide").
- [ ] **Step 2: Write `GUIDE.md`** (English, for agy, ≤ 150 lines). It covers:
  - **Transcreation, not translation:** write for a native viewer of that country who does not know Vietnam.
  - **Per beat:** keep the beat's goal and facts; free sentence count; new hooks and jokes that work in that culture; no puns that need Vietnamese.
  - **Explain context a foreign viewer lacks**, but only with the beat's facts.
  - **Names** from the glossary; the first mention gets a short gloss ("Tran Hung Dao, the Trần prince who led the defence") only if the facts say so.
  - **Units and dates** in local formats; numbers as digits.
  - **Per-language notes:**
    - en: US spelling, contractions OK.
    - ja: です/ます narration, short sentences, no katakana slang overload.
    - de: Du for viewers, avoid long compounds.
    - es: neutral Latin-American Spanish, tú.
  - **The certainty words in each language:** tương truyền → "legend says / 伝説によると / der Legende nach / según la leyenda"; cho thấy → "suggests / 示している / deutet darauf hin / sugiere".
- [ ] **Step 3: Seed `stylebook/<lang>.json`** with the rules of `vi.json` rewritten for that language (`kept`), plus the guide's per-language notes.
- [ ] **Step 4: Tests.** `test_each_lang_has_core_rules` checks each book has ≥ 10 kept rules and one about the certainty words. Run it.
- [ ] **Step 5: Commit** `docs: localization guide and per-language style books`.

---

### Task 3: agy rewrite + automatic checks + Claude language review

**Files:**
- Create:
  - `tools/longform/langscript.py`
  - `tools/longform/prompts/rewrite.md`
  - `tools/longform/prompts/review_lang.md`
- Modify: `tools/longform/workers.py`, `tools/longform/script.py` (allow a `lang` argument for paths)
- Test: `tools/longform/tests/test_langscript.py`

**Interfaces:**
- Produces:
  - **Language-aware script API.** `script.load/save/update/report/colour/approve` accept `lang=None`. `None` or the source language uses `script/`; others use `lang/<code>/script/`. Progress for other languages goes to `progress.set_lang(pdir, lang, "script", …)`.
  - `langscript.outline(pdir) -> [{"beat", "goal", "facts": [ids], "chapter"}]`, from the **approved** source script.
  - `langscript.check(pdir, lang) -> {"report": script.report(...), "problems": [str], "per_sentence": {sid: [reasons]}}`. On top of the colour report it adds:
    - a fact outside its beat's list → red reason "dữ kiện không thuộc cảnh này";
    - glossary misses → yellow;
    - beats missing or extra → whole-script problem.
  - **Job kind `agy_rewrite`** (lane `agy`), params `{"project", "lang"}`:
    - `build` refuses unless the source script is approved and `lang` is a project language other than vi;
    - the run folder holds `outline.json` (beats with goals and **fact claims and quotes**, no source sentences), `glossary.json`, `style.md` (that language), `GUIDE.md` and `REWRITE.md` (prompt, with `base_version`);
    - the result is the script shape;
    - `on_end`:
      - `workers.validate_script(result, allowed = the union of beat facts)`, plus the same beat id set as the outline (else refused whole);
      - then `script.save(pdir, data, "agy", lang=lang)`, with sentences `reviewed=False`;
      - then a `lang_check` record and a `claude_review_lang` job.
  - **Job kind `claude_review_lang`** (lane `claude`):
    - the run folder holds the language script, outline, glossary, style and the check results;
    - Claude fixes problems in place, never adds facts, keeps the beat ids, and writes `result.json` = the script plus `"flags": [{"sentence", "issue", "back_translation_vi"}]`;
    - `on_end` validates, then saves (`reviewed=True`, base version check). Then:
      - when the check has no red, no glossary misses and no flags, it approves automatically (`script.approve(..., by="auto", lang=lang)`);
      - otherwise one inbox item per flag, `lang_flag` "<LANG> câu <sid>: <issue> — dịch lại: <back_translation_vi>" (screen `langs`).
- [ ] Steps: failing tests, using the fake agy/claude from Plan 3 `test_workers.Base`.
  - `test_outline_has_no_source_sentences`
  - `test_rewrite_requires_approved_source`
  - `test_missing_beat_refused`
  - `test_fact_outside_beat_red`
  - `test_number_not_in_facts_red`
  - `test_glossary_miss_yellow`
  - `test_review_clean_auto_approves`
  - `test_review_flags_go_to_inbox_with_back_translation`
  - `test_vi_paths_unchanged`
- Then run, implement, run, commit `feat: per-language rewrite by agy with checks and Claude review`.

---

### Task 4: Voice parts + mp3 drop-in

**Files:**
- Create: `tools/longform/voice.py`
- Modify: `config/languages.json` (per language `chars_per_second`: vi 15.5 (Vbee at 1.13), en 15, ja 7.5, de 14, es 15; `max_part_seconds`: vi 55, others null; `max_part_chars`: vi null, others 4500)
- Test: `tools/longform/tests/test_voice.py`

**Interfaces:**
- Produces:
  - `voice.split(sentences: list[(id, text)], lang_cfg) -> list[{"part": "01", "sentences": [ids], "text": str, "seconds": float, "flags": [str]}]`:
    - greedy packing by sentence;
    - a single sentence over the limit becomes its own part with the flag "câu dài hơn giới hạn …, cắt bằng tay".
  - `voice.prepare(pdir, lang) -> list`:
    - writes `lang/<code>/audio/parts/NN.txt` (the text to paste) and `parts.json` (Plan 5 format: `part`, `file` = `NN.mp3`, `sentences`);
    - adds inbox `voice_needed` "Giọng <LANG>: N phần chờ bạn tạo (<engine>)" (screen `langs`, key `voice:<pid>:<lang>`);
    - refuses while that language's script is not approved.
  - `voice.drop(pdir, lang, name, data: bytes) -> dict`:
    - accepts only `NN.mp3` names listed in `parts.json`, mp3 magic bytes (`ID3` or frame sync `0xFFE`), ≤ 50 MB;
    - saves to `lang/<code>/audio/parts/NN.mp3`;
    - when all parts are present, enqueues the `timing` job (kind `timing_build`, lane `cpu`, `python -m tools.longform.timing <pid> <lang>`) and resolves the inbox item.
  - `voice.status(pdir, lang) -> {"parts": [{"part", "chars", "seconds", "present", "flags"}], "missing": [...]}`.
  - Editing the script after `prepare` marks the parts stale (`parts.json` gets `"stale": true` when the sentence lists differ), and the UI shows "phần giọng cũ, chuẩn bị lại".
- [ ] Steps: failing tests.
  - `test_split_respects_seconds`
  - `test_split_respects_chars`
  - `test_long_sentence_own_part_flagged`
  - `test_prepare_writes_parts_and_inbox`
  - `test_drop_unknown_part_refused`
  - `test_drop_non_mp3_refused`
  - `test_timing_waits_for_all_parts`
  - `test_stale_after_edit`
- Then run, implement, run, commit `feat: voice parts per tool limits and mp3 drop-in`.

---

### Task 5: Upload texts per language

**Files:**
- Create: `tools/longform/upload.py`, `tools/longform/prompts/upload_texts.md`
- Modify: `tools/longform/workers.py`
- Test: `tools/longform/tests/test_upload.py`

**Interfaces:**
- Produces:
  - Job kind `agy_upload_texts` (lane `agy`), params `{"project", "lang"}`:
    - the run folder holds that language's approved script, the chapter titles, the chapter start times from the timing (if present), and the source names used (the fact-bank source titles linked from approved sentences);
    - agy writes `result.json` `{"title", "description", "tags": [...]}`.
  - `upload.validate(texts, lang) -> list[str]`. It refuses:
    - a title over 100 characters;
    - a description containing `http`, or "minh họa bằng AI" (or AI-disclaimer lines in other languages);
    - a description without exactly one sources line (its prefix comes from `labels.sources_line[lang]`, e.g. "Nguồn:", "Sources:", "出典:", "Quellen:", "Fuentes:");
    - tags totalling over 500 characters.
  - `upload.chapters(pdir, lang) -> str` from the timing (`0:00 …` first).
  - `upload.write(pdir, lang, texts)`: `lang/<code>/upload/upload.md` (title, description, chapters appended, tags, plus the line "Khi upload: đặt nội dung thay đổi/tổng hợp = Có").
  - `on_end` runs `validate`, then `write`, then sets the progress `upload` step to `wait`.
- [ ] Steps: failing tests.
  - `test_refuses_links_and_ai_line`
  - `test_one_sources_line`
  - `test_chapters_from_timing`
  - `test_write_upload_md`
- Then run, implement, run, commit `feat: per-language upload texts`.

---

### Task 6: Japanese font, line breaking, thumbnail

**Files:**
- Download (its own folder, then copy only the font): `NotoSansJP` variable or Bold TTF from `https://github.com/google/fonts/tree/main/ofl/notosansjp` (OFL). Put it in `tools/kit/fonts/` and record it in `LICENSES.md` (URL, SHA-256, OFL).
- Create in `tools/anim/src/longform/`:
  - `jabreak.ts` + `jabreak.test.ts`;
  - `Thumb.tsx` (composition `Thumb`, 1280x720 still).
- Modify: `Root.tsx`, `Cards.tsx` (use `jabreak` when lang is `ja`), `tools/longform/render.py` (`render_thumb`), `workers.py` (kind `render_thumb`, lane `render`)

**Interfaces:**
- `jabreak.lines(text, maxChars) -> string[]`: breaks between characters, never violating the kinsoku sets in Global Constraints.
- `<Thumb bg hero title lang />`:
  - an approved background (a crop);
  - an approved hero pose, large, on the right;
  - a title of 2 lines at most, ink outline and paper-colour fill, shrinking to fit.
- `render.render_thumb(pdir, lang, bg_item, hero_key, title)` writes `lang/<code>/upload/thumb.png`.
- [ ] Steps: failing tests.
  - `jabreak.test.ts`: `no line starts with closing punctuation`, `no line ends with opening bracket`, `latin words not split`.
  - Python `test_render_thumb_props`.
- Then download the font and check its hash, implement, run, commit `feat: Japanese font and line breaking, code-drawn thumbnail`.

---

### Task 7: Languages tab UI

**Files:**
- Create: `studio/static/langs_view.js`
- Modify: `studio/server.py`, `app.js`, `lib.js`, `style.css`, `lib.test.js`
- Test: new `test_server.py` cases plus lib tests

**Interfaces:**
- API (per project `<id>` and language `<lang>`):
  - `GET …/langs/<lang>` → `{script, check, voice, timing, upload, render}`;
  - `POST …/langs/<lang>/rewrite`;
  - `POST …/langs/<lang>/review`;
  - `POST …/langs/<lang>/approve`;
  - `POST …/langs/<lang>/voice/prepare`;
  - `GET …/langs/<lang>/voice/parts/<NN>.txt`;
  - `POST …/langs/<lang>/voice/drop` `{"name", "data": base64}`;
  - `POST …/langs/<lang>/upload_texts`;
  - `POST …/langs/<lang>/thumb` `{"bg", "hero", "title"}`;
  - `POST /api/projects/<id>/languages` `{"add": "de"}`: adds a configured language to the project and creates its folders.
- UI (`#/p/<id>/langs`):
  - Language tabs (VI is the source, read-only here) plus "+".
  - Per language:
    - **Script panel:** beat by beat. The left side shows the beat goal and fact chips; the right side shows that language's sentences, coloured like Plan 3, with flags and back-translations.
    - Buttons "Viết lại (agy)", "Soát (Claude)", "Chốt".
    - **Voice panel:** the parts list with seconds and characters, a "Copy" button per part (the text), the file name to save as, present/missing status, and a drop zone accepting several mp3 files at once.
    - **Render panel** (Plan 5 button) and **Upload panel:** title, description and tags with copy buttons; the chapters; the thumbnail preview with "Tạo thumbnail".
- [ ] Steps: failing tests.
  - `test_lang_endpoint_shape`
  - `test_voice_drop_route`
  - `test_add_language`
  - lib `voiceSummary`, `langTabState`
- Then run, implement, run. Take screenshots with a fixture root on port 8799 (light, dark, 500 px) and fix what is broken. Commit `feat: Studio languages tab`.

---

### Task 8: Docs

- [ ] Update `CLAUDE.md` (folder map, the new jobs), `HANDOFF.md` (state: Plans 1–6 built; what the owner does per video, step by step) and `studio/README.md` (job kinds table).
- [ ] Run all suites.
- [ ] Commit `docs: full long-form workflow handoff`.
