# Plan 3: Script chat + fact bank — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill Studio's "Kịch bản" tab:
- the owner chats with AI;
- agy gathers sources and writes the first draft;
- Claude verifies every fact against the saved source text, then reviews the draft;
- every factual sentence links to verified facts;
- red sentences block "Chốt kịch bản".

**Architecture:** Data lives in project files:
- `research/sources.json`;
- `research/facts.jsonl`;
- `research/pages/NNN.txt` (saved page text);
- `script/script.json` (chapters → beats → sentences);
- `library/stylebook/<lang>.json`.

Pure logic modules in `tools/longform/`:
- `factbank.py`: storage, import, verbatim check;
- `script.py`: schema, sentence colours, approve gate;
- `stylebook.py`.

Four new job kinds run through Plan 2's queue. Each kind's prompt is a template in `tools/longform/prompts/`. Each worker writes one JSON result file, and the kind's `on_end` imports that file:
- `agy_research`;
- `claude_verify`;
- `agy_draft`;
- `claude_review`.

The chat is a fifth kind, `agy_chat`: the owner's message goes straight to agy, never through Claude (owner, 2026-10-31). Studio gives agy the script, the fact bank and the style rules as a context file. agy answers with a structured result that Studio applies. Claude takes part only through the verify and review jobs that Studio starts. The UI is a three-column screen: Chat | Ngân hàng dữ kiện | Kịch bản.

**Tech Stack:** Python 3.9 stdlib + Pillow (existing); Plan 2 `jobs`, `inbox`, `progress`, `claude_box`; agy CLI (`~/.local/bin/agy`, `--sandbox`, no shell commands, never skip-permissions); `claude -p` (subscription); vanilla JS ES modules.

**Spec:** `docs/superpowers/specs/2026-10-31-longform-workflow-design.md` §3, §4.4 (binding), §4.7 (beat is the cross-language unit) · Roadmap · Mockup `.superpowers/brainstorm/34991-1793441859/content/script-chat.html`

## Global Constraints

- Plan 2 constraints all still hold: Studio stays on `127.0.0.1`, the cross-site guard, argv built server-side only, never skip-permissions for Claude or agy, Vietnamese UI text, no new dependencies.
- **No invented facts** (spec §4.4):
  - A fact needs a verbatim quote that is found in its saved page text. Code checks this; a model's word is not enough.
  - AI-written sentences may use only facts already in the bank.
  - Grades follow the spec, not the agy task file:
    - **A**: scholarship, museum, heritage agency, published translation of a primary record.
    - **B**: major newspaper, encyclopedia.
    - **C**: blog, travel site, wiki.
  - A number needs 1 verified A, or 2 verified B from different sources. C alone never suffices.
- Certainty words: legend → "tương truyền"; debated → "có ý kiến cho rằng"; archaeology → "cho thấy", never "chứng minh". `script.py` flags sentences that break these rules.
- Conflicting records: each version is its own fact, linked by `conflicts_with`. A sentence that uses a conflicted fact is yellow, never green.
- Voice (spec §4.4):
  - a history storyteller; short sentences; light humour;
  - "bạn", never "chúng ta" or "bạn nhỏ";
  - no English slang;
  - no source names spoken.
  - `stylebook/vi.json` is seeded with these rules.
- Beat id is the alignment unit across languages (Plan 6 depends on it): `B01`, `B02`, … stable across versions.
- Division of work (owner, 2026-10-31):
  - agy: research and first draft.
  - Claude: verification and review.
  - The verifier is never the writer.
- Python tests: `.venv/bin/python -m unittest discover -s tools/longform/tests -v`
- UI tests: `node --test studio/static/`
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **agy quotes a sentence that is not on the page it saved** (hallucinated or paraphrased quote). The fact becomes `rejected` with note "trích không có trong trang đã lưu" and never turns green (Task 1, `test_quote_not_in_page_rejected`).
2. **A sentence has a number backed only by one B or by C sources.** The sentence is red, and "Chốt kịch bản" is refused by the API, not only greyed in the UI (Task 2, `test_number_needs_a_or_two_b`, Task 6 `test_approve_refused_with_red`).
3. **agy or Claude writes a malformed result file** (bad JSON, missing ids, unknown fact ids). The import rejects it with an inbox item; the bank and the script are unchanged (Task 4, `test_import_bad_result_keeps_bank`).
4. **The owner edits a sentence after approval.** The approval is cleared, and the script step goes back to `wait` (Task 2, `test_edit_clears_approval`).
5. **The same source is imported twice** (two research runs find one URL). One source and no duplicate facts: the dedupe key is URL plus normalised quote (Task 1, `test_reimport_dedupes`).

---

### Task 1: Fact bank (sources, facts, verbatim check, import)

**Files:**
- Create: `tools/longform/factbank.py`
- Test: `tools/longform/tests/test_factbank.py`

**Interfaces:**
- Produces:
  - `factbank.STATUSES = ("pending", "verified", "weak", "conflict", "rejected")`. UI icons: ⏳ ✅ ⚠️ ⛔ ✖.
  - Source `{"id": "S001", "title", "publisher", "url", "file", "page_file", "grade", "kind"}` in `research/sources.json`. `file` is for uploads in `research/uploads/`; `page_file` is `research/pages/NNN.txt`, whose first line is the URL or file name.
  - Fact (one JSON object per line in `research/facts.jsonl`):
    - Fields: `{"id": "F001", "claim", "quote", "quote_lang", "source", "location", "grade", "reports", "legend", "conflicts_with": [], "status", "checked_by", "check_note", "checked_at", "origin"}`.
    - `origin` is the research run id.
  - `factbank.load(pdir) -> (sources: dict[id, dict], facts: dict[id, dict])`
  - `factbank.normalise(text) -> str`:
    - NFC, lowercase;
    - unify quotes and dashes;
    - collapse whitespace;
    - strip `…`/`...` at the ends.
  - `factbank.quote_in_page(quote, page_text) -> bool`: the normalised quote must be a substring. For a quote with an inner `…`, every part (each ≥ 12 chars) must appear in order.
  - `factbank.import_research(pdir, run_dir, origin) -> dict`:
    - Reads `run_dir/sources.jsonl` (the format in `projects/001-bach-dang-1288/research/agy/TASK.md`).
    - Copies the pages into `research/pages/`.
    - Adds sources (dedupe by URL, else by file name) and facts (dedupe by source + normalised quote).
    - Each new fact gets `status="pending"`, or `"rejected"` with `check_note="trích không có trong trang đã lưu"` when `quote_in_page` fails or the page file is missing.
    - Rewrites `conflicts_with` ids from run ids to bank ids.
    - Returns `{"sources_added", "facts_added", "rejected", "duplicates"}`.
    - Raises `ValueError` and changes nothing on malformed input (bad JSON line, missing `quote`/`url`/`claim`).
  - `factbank.set_status(pdir, fact_id, status, by, note) -> dict` sets `checked_at` to an ISO timestamp.
  - `factbank.supports_number(facts: list[dict], sources) -> bool`: true when the verified facts include grade A, or grade B from ≥ 2 different source ids.
- [ ] **Step 1: Write failing tests:**
  - `test_normalise_quotes_and_space`
  - `test_quote_in_page_exact`
  - `test_quote_in_page_with_ellipsis`
  - `test_quote_not_in_page_rejected`: import a run whose quote is paraphrased; the fact is `rejected` with the note.
  - `test_import_counts`
  - `test_reimport_dedupes`
  - `test_conflicts_rewritten`
  - `test_bad_line_changes_nothing`
  - `test_supports_number`: one A gives True; one B gives False; two B from the same source give False; two B from different sources give True; C gives False; a non-verified A gives False.
- [ ] **Step 2: Run** `.venv/bin/python -m unittest tools.longform.tests.test_factbank -v`. Expected: FAIL (ImportError).
- [ ] **Step 3: Implement** `factbank.py`. Writes are atomic (temp + `os.replace`), under an `fcntl` lock on `research/.bank.lock`.
- [ ] **Step 4: Run.** Same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: fact bank with verbatim quote check and research import`.

---

### Task 2: Script model, sentence colours, approve gate

**Files:**
- Create: `tools/longform/script.py`
- Test: `tools/longform/tests/test_script.py`

**Interfaces:**
- Consumes: `factbank.load`, `factbank.supports_number`, `progress.set_step`.
- Produces:
  - `script/script.json`:
    - `{"lang": "vi", "version": int, "approved": bool, "approved_at", "chapters": [{"id": "C01", "title", "beats": [{"id": "B01", "goal", "sentences": [{"id": "s001", "text", "facts": ["F001"], "kind": "fact|narration|question|joke", "note"}]}]}]}`.
    - Earlier versions are kept as `script/versions/vNNN.json`.
  - `script.load(pdir) -> dict | None` and `script.save(pdir, data, by) -> int`:
    - `save` bumps the version and archives the previous one.
    - It clears `approved` when any sentence text or fact list changed.
    - It sets the `script` step to `doing`.
  - `script.is_factual(sentence) -> bool`. True when any of these holds:
    - `kind == "fact"`;
    - the text has a digit;
    - the text has a capitalised word that is not the first word and not in `NOT_NAMES`.
    - `NOT_NAMES` is `{"Bạn"}` plus words after `:`.
  - `script.colour(sentence, sources, facts) -> {"colour": "red|yellow|green|plain", "reasons": [str]}`, where `reasons` are Vietnamese:
    - **red**:
      - factual with no verified fact;
      - a linked fact id that does not exist or is rejected;
      - a digit not supported by `supports_number`;
      - "chứng minh" next to an archaeology fact;
      - a `legend` fact without "tương truyền" in the text;
      - "chúng ta" or "bạn nhỏ" in the text.
    - **yellow**: any linked fact is `weak` or `conflict`.
    - **green**: factual and every fact is verified.
    - **plain**: not factual.
  - `script.report(pdir) -> {"sentences": [{id, beat, colour, reasons}], "red": n, "yellow": n, "green": n}`.
  - `script.approve(pdir, by) -> dict`:
    - Raises `ValueError("còn N câu đỏ")` when red > 0.
    - Otherwise sets `approved=True`, sets the `script` step to `done`, and resolves inbox key `script:<pid>`.
- [ ] **Step 1: Write failing tests:**
  - `test_is_factual`
  - `test_colour_green`
  - `test_colour_red_no_fact`
  - `test_colour_red_rejected_fact`
  - `test_number_needs_a_or_two_b`
  - `test_yellow_conflict`
  - `test_legend_needs_tuong_truyen`
  - `test_chung_minh_red`
  - `test_banned_words_red`
  - `test_save_versions`
  - `test_edit_clears_approval`
  - `test_approve_refused_with_red`
  - `test_approve_sets_step_done`
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement** `script.py`.
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: script model with fact-linked sentence colours and approve gate`.

---

### Task 3: Style book (per language, self-learning)

**Files:**
- Create: `tools/longform/stylebook.py`, `library/stylebook/vi.json`
- Test: `tools/longform/tests/test_stylebook.py`

**Interfaces:**
- Produces:
  - `library/stylebook/<lang>.json`: `{"lang", "rules": [{"id": "R01", "text", "status": "kept|proposed|dropped", "from", "added"}], "examples": [paths]}`.
  - `stylebook.load(lang) -> dict` (empty book when the file is missing).
  - `stylebook.kept(lang) -> list[str]`.
  - `stylebook.propose(lang, text, source) -> dict`: adds a `proposed` rule and an inbox item of kind `style_rule` (key `style:<lang>:<id>`, no Telegram).
  - `stylebook.decide(lang, rule_id, keep: bool)`: sets `kept` or `dropped` and resolves the inbox item.
  - `vi.json` is seeded with the spec §4.4 voice rules as `kept` rules, one rule per line of that paragraph. Its `examples` list the four archived Short scripts: `/Users/quoctung/Documents/AI/archive/2026-10-31/vn-history-shorts/*/script/script.txt`.
- [ ] **Step 1: Write failing tests:**
  - `test_seed_has_core_rules`: `vi` includes rules mentioning "bạn" and "chúng ta".
  - `test_propose_then_keep`
  - `test_drop`
  - `test_missing_lang_empty`
- [ ] **Steps 2–4:** Run, implement, run. Expected: FAIL, then PASS.
- [ ] **Step 5: Commit** `feat: per-language style book with proposed rules`.

---

### Task 4: AI workers (agy research, Claude verify, agy draft, Claude review)

**Files:**
- Create:
  - `tools/longform/agy.py` (shared agy argv);
  - `tools/longform/workers.py` (the 4 job kinds);
  - `tools/longform/prompts/research.md`, `verify.md`, `draft.md`, `review.md`
- Test: `tools/longform/tests/test_workers.py`

**Interfaces:**
- Consumes: `jobs.Kind/register/enqueue`, `factbank.*`, `script.*`, `stylebook.kept`, `inbox.add`, `claude_box.config`.
- Produces:
  - `agy.argv(prompt: str) -> list[str]`: `[AGY, "-p", prompt, "--model", MODEL, "--sandbox", "--output-format", "json", "--print-timeout", "0"]`. It never includes `--dangerously-skip-permissions`.
  - agy workers use only built-in `search_web`, URL reading and file tools. Every prompt says "never run shell commands, never call MCP tools" (a denied call ends the run; perplexity MCP was denied on 2026-10-31): headless agy denies the `command` permission, and a `--settings` allowlist was tested on 2026-10-31 and did not apply.
  - `agy.denied(result_json) -> list[str]` reads `denied_actions` from agy's JSON output. When it is non-empty and no result file exists, the job fails with "agy bị chặn quyền: <actions>".
  - The four job kinds. Each job works in its own run folder `research/runs/<kind>-<n>/` (n = next free number), which is also its `cwd`. Each writes exactly one result file, `result.json`, or `sources.jsonl` for research.

| Kind | Lane | Params | Worker | Result | `on_end` when `done` |
|---|---|---|---|---|---|
| `agy_research` | agy | `{"project", "request"}` | agy with `research.md` (TASK.md rules + the request) | `sources.jsonl` + `pages/` | `factbank.import_research`, then enqueue `claude_verify` for the new pending facts in batches of 15; inbox "Đã tìm N nguồn, M dữ kiện" (no Telegram) |
| `claude_verify` | claude | `{"project", "facts": [ids]}` | Claude with `verify.md`: for each fact, read `research/pages/…`, answer whether the quote says the claim, re-grade the source per spec | `result.json` `[{"id", "status": "verified|weak|rejected", "grade", "note"}]` | `factbank.set_status` (by `claude`); a fact whose `conflicts_with` is non-empty and that would be `verified` becomes `conflict` |
| `agy_draft` | agy | `{"project", "request"}` | agy with `draft.md`: verified/weak/conflict facts only, kept style rules, chapter outline, 10–15 min (~1,500–2,200 words vi) | `result.json` in the `script.json` shape | `script.save(by="agy")`; enqueue `claude_review` |
| `claude_review` | claude | `{"project"}` | Claude with `review.md`: checks each sentence against its facts, the style rules and the conflict rule (both versions, plain words, 1–3 per video); rewrites sentences in place; may drop facts, never adds new ones | `result.json`: the revised script plus `"notes": [{"sentence", "note"}]` | `script.save(by="claude")`; `progress.set_step(script, "wait")`; inbox `script_approve` "Kịch bản v<N> chờ bạn chốt (đỏ X, vàng Y)" with key `script:<pid>` |

  - Any import error (bad JSON, unknown fact ids in the draft, wrong shape) gives an inbox `job_failed` item "Kết quả của <kind> không dùng được: <why>"; the bank and the script stay unchanged.
  - Prompts state the rules verbatim from spec §4.4 and point the worker at absolute paths. The Claude prompts (verify, review) tell Claude to write `result.json` with the Write tool and nothing else.
- [ ] **Step 1: Write failing tests.** Use fake kinds: register the real kinds with `agy.AGY` and the `claude` binary patched to a Python script that copies a fixture into the run folder.
  - `test_agy_argv_no_skip`
  - `test_agy_denied_fails_job`
  - `test_research_imports_and_queues_verify`
  - `test_verify_applies_statuses`
  - `test_verify_conflict_status`
  - `test_draft_saves_and_queues_review`
  - `test_draft_unknown_fact_rejected`
  - `test_review_sets_wait_and_inbox`
  - `test_import_bad_result_keeps_bank`
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `feat: agy research/draft and Claude verify/review workers`.

---

### Task 5: Script chat (agy directly, no Claude in between)

Owner rule, 2026-10-31: on the dashboard, agy work runs as agy itself; Claude never launches or relays agy. The chat goes straight to agy. Claude takes part only through the `claude_verify` and `claude_review` jobs, which Studio starts.

**Files:**
- Create: `tools/longform/chat.py`, `tools/longform/prompts/chat.md`
- Test: `tools/longform/tests/test_chat.py`

**Interfaces:**
- Consumes: `agy.argv`, `jobs.Kind/register/enqueue`, `factbank.load`, `script.load/save`, `stylebook.kept/propose`.
- Produces:
  - Job kind `agy_chat`, lane `agy`, params `{"project", "message"}`.
  - **Context.** `build` writes a context file in a new run folder `research/runs/agy_chat-<n>/`:
    - the last 20 chat lines from `script/chat.jsonl`;
    - the current script, with sentence ids, colours and facts;
    - the fact bank, as a compact list of `id`, `status`, `claim`;
    - the kept style rules.
  - **Prompt.** `prompts/chat.md` says:
    - answer the owner in Vietnamese;
    - use only facts in the bank;
    - never run shell commands or call MCP tools;
    - write exactly one `result.json`.
  - **Result format** (`result.json`): `{"reply": str, "edits": [{"op": "set|add|delete", "id", "beat", "after", "text", "facts"}], "research": str | null, "draft": str | null, "rule": str | null}`.
  - **`on_end`** (when the job is `done`):
    - append the owner's message and `reply` to `script/chat.jsonl`;
    - apply `edits` through `script.save(by="agy-chat")`, after checking every fact id exists and is not rejected. A bad edit is refused whole, and the reply says why;
    - `research`, if present, enqueues `agy_research` directly;
    - `draft`, if present, enqueues `agy_draft` directly;
    - `rule`, if present, calls `stylebook.propose`.
  - `chat.history(pdir) -> list[dict]`: the last 50 entries `{"role": "owner"|"agy"|"system", "text", "at"}`.
  - The chat buttons map straight to jobs, with no AI routing:
    - "Tìm tư liệu" → `agy_research`;
    - "Viết nháp" → `agy_draft`;
    - "Soát lại" → `claude_review`.
- [ ] **Step 1: Write failing tests:**
  - `test_build_writes_context_no_claude`: the argv starts with the agy binary, and `"claude"` is not in the argv.
  - `test_edits_applied`
  - `test_edit_with_rejected_fact_refused_whole`
  - `test_research_request_enqueues_agy_research`
  - `test_rule_proposed`
  - `test_bad_result_keeps_script`
- [ ] **Steps 2–4:** Run, implement, run. Expected: FAIL, then PASS.
- [ ] **Step 5: Commit** `feat: script chat runs agy directly`.

---

### Task 6: Script API

**Files:**
- Modify: `studio/server.py`
- Test: `tools/longform/tests/test_server.py` (new cases)

**Interfaces:**
- Produces:

| Method | Path | Does |
|---|---|---|
| GET | `/api/projects/<id>/facts` | `{"sources", "facts"}` |
| GET | `/api/projects/<id>/pages/<NNN>` | the saved page text (`NNN` is 3 digits, looked up in the bank) |
| GET | `/api/projects/<id>/script` | `{"script", "report"}` (script may be null) |
| POST | `/api/projects/<id>/script/sentence` | `{"id", "text", "facts"}` → saves |
| POST | `/api/projects/<id>/script/approve` | `script.approve`, or 400 with the red count |
| POST | `/api/projects/<id>/research` | `{"request"}` → `agy_research` job |
| POST | `/api/projects/<id>/draft` | `{"request"}` → `agy_draft` job |
| POST | `/api/projects/<id>/review` | → `claude_review` job |
| POST | `/api/projects/<id>/chat` | `{"message"}` → `agy_chat` job (agy directly) |
| GET | `/api/projects/<id>/chat` | `chat.history` |
| POST | `/api/projects/<id>/facts/<F>/status` | owner override `{"status", "note"}` (by `owner`) |
| POST | `/api/projects/<id>/sources/upload` | `{"name", "data": base64}` ≤ 30 MB, PDF/JPG/PNG/TXT only → `research/uploads/`; then an `agy_research` job with request "rút dữ kiện từ file <name>" |
| GET | `/api/stylebook/<lang>` | the book |
| POST | `/api/stylebook/<lang>/<R>/decide` | `{"keep"}` |

- [ ] **Step 1: Write failing tests:**
  - `test_facts_endpoint`
  - `test_page_endpoint_only_bank_pages`
  - `test_script_endpoint_report`
  - `test_approve_refused_with_red`
  - `test_upload_type_and_size_checked`
  - `test_stylebook_decide`
- [ ] **Steps 2–4:** Run, implement, run. Expected: FAIL, then PASS.
- [ ] **Step 5: Commit** `feat: script, fact bank and style book API`.

---

### Task 7: Script screen (3 columns)

**Files:**
- Modify: `studio/static/app.js`, `studio/static/style.css`, `studio/static/lib.js`
- Test: `studio/static/lib.test.js`

**Interfaces:**
- Produces (`lib.js`):
  - `factIcon(status)` maps ⏳ ✅ ⚠️ ⛔ ✖.
  - `colourClass(c)`.
  - `summaryLine(report)` returns `"đỏ 2 · vàng 5 · xanh 40"`.
  - `canApprove(report)`.
- Layout, on the `#/p/<id>/script` tab:
  - **Chat** column: history plus an input. Buttons "Tìm tư liệu" (asks for the request text), "Viết nháp", "Soát lại". Messages go to `/chat`.
  - **Ngân hàng dữ kiện** column:
    - Filter chips by status, with counts.
    - Each row shows icon, id, claim and grade.
    - Clicking a row opens a detail panel: quote in a blockquote, source title with link, a "Xem trang đã lưu" button, who checked it and the note, and owner buttons ✅/⚠️/✖.
    - "+ Thêm nguồn" offers a URL (becomes a research request) or a file upload.
  - **Kịch bản** column:
    - Chapters → beats → sentences.
    - Each sentence has a left border coloured by its colour, its fact chips and its reasons on hover.
    - Click a sentence to edit it inline (textarea plus fact ids) and save.
    - The top shows `summaryLine` and the "Chốt kịch bản" button, enabled only when `canApprove`.
  - **Proposed style rules** show as cards above the chat: "Giữ" / "Bỏ".
  - Below 1100 px the three columns become tabs.
- [ ] **Step 1:** Write failing tests for the four helpers. **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Screenshot in light and dark (headless Chrome, 1400 px and 500 px) with fixture data in a temp project. Fix what looks broken.
- [ ] **Step 6: Commit** `feat: Studio script screen (chat, fact bank, script)`.

---

### Task 8: First real run on 001-bach-dang-1288 and owner check

- [ ] **Step 1: Import the research.**
  - Import the research agy has already gathered (`projects/001-bach-dang-1288/research/agy/`) with `factbank.import_research`.
  - Enqueue `claude_verify` for all pending facts.
  - Report the counts: verified, weak, conflict, rejected (with how many were rejected by the verbatim check).
- [ ] **Step 2: Draft and review.** Once verification is done, enqueue `agy_draft` with the request: "Video 10–15 phút: hook so sánh với Nhật → sức mạnh Mông Cổ → hai lần đầu → 1287–1288 và Vân Đồn → bãi cọc và con nước → trận đánh → khảo cổ → kết; 1–3 chỗ vênh quan trọng nhất". `claude_review` follows on its own.
- [ ] **Step 3: Owner check.**
  - Send the owner the link `#/p/001-bach-dang-1288/script`. Ask them to read the draft, try the chat ("viết lại câu s012 cho vui hơn"), and check a few fact quotes.
  - Record the verdict in the ledger. Fixes inside this plan's scope get done; content changes go through the chat.
- [ ] **Step 4:** Run all suites; commit any fixes.
