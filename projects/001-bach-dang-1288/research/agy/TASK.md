# Research task: sources for a 10–15 minute video, "Bạch Đằng 1288"

You are the research worker for a Vietnamese history YouTube channel. The video tells the third Mongol–Yuan
invasion of Đại Việt (1287–1288) and the Battle of Bạch Đằng (spring 1288). Your job is to **collect sources and
quotes**, not to write the script.

## Absolute rules

1. **Never invent anything.** Every claim must come from a page or document you actually opened in this session.
2. **The `quote` field is copied verbatim** from the opened text, in its original language. Do not paraphrase,
   translate, fix spelling, or join sentences from different places. If you cannot find a verbatim sentence that
   supports the claim, do not record the claim.
3. Save the text of every page you quote as `pages/NNN.txt` (NNN = 001, 002, …). Put the URL on the first line and
   the readable page text below it. `page_file` points to that file.
4. When records disagree (for example Đại Việt sử ký toàn thư against Nguyên sử or An Nam chí lược, or different
   army or ship numbers), record **each version as its own claim** and link them with `conflicts_with`. Say who
   reports what.
5. Legends and traditions are marked `"legend": true` (for example sayings attributed to people, or temple stories).
6. Numbers (troops, ships, dates, stake counts) always say who gives them (`reports`).
7. Wikipedia and blogs may be used only to find better sources. If you quote them anyway, grade them C.
8. `old_shorts_hints.csv` holds notes from an earlier short video. Use them only as hints for what to look for.
   They are **not** sources and are partly about the battle of 938, not 1288.

## Grades

- **A**: a primary historical record (Đại Việt sử ký toàn thư, Nguyên sử, An Nam chí lược, Việt sử lược, or a
  published translation of one), a peer-reviewed paper, or an archaeological report.
- **B**: a reputable secondary source: a national museum, a university or academy publication, an encyclopedia
  with editors, or a government heritage page.
- **C**: anything else: news, blogs, Wikipedia, forums.

## Topics to cover (as many as the sources allow)

1. Background: the first (1258) and second (1285) invasions, in brief.
2. The 1287 invasion: forces, commanders (Thoát Hoan / Toghan, Ô Mã Nhi / Omar, Phàn Tiếp, …), routes.
3. The Yuan supply fleet and the battle at Vân Đồn (Trần Khánh Dư, Trương Văn Hổ), and why losing the grain mattered.
4. Thăng Long abandoned again; the Yuan army short of food; the decision to withdraw.
5. Trần Hưng Đạo's plan at Bạch Đằng: the stakes, the tide, where and when (lunar date, Mậu Tý year).
6. The battle itself: what the records say happened, ships taken or sunk, commanders captured (Ô Mã Nhi, Phàn Tiếp, …).
7. Thoát Hoan's retreat by land, and the aftermath (prisoners, envoys, tribute, peace).
8. Archaeology of the stake fields (Yên Giang, Đồng Vạn Muối, Đồng Má Ngựa, Cao Quỳ …): what was found, when, dating.
9. Trần Hưng Đạo: who he was, his role, the "Hịch tướng sĩ" (only what sources say about it).
10. Anything a careful viewer might ask that the records answer (the weather, the season, the tide range at Bạch Đằng).

## Output

Write two files in this folder (and nothing outside this folder):

### `sources.jsonl`, one JSON object per line:

```json
{"id": "S001", "topic": 5, "claim_vi": "short claim in Vietnamese",
 "quote": "verbatim text from the page", "quote_lang": "vi|zh|en|fr|…",
 "source_title": "…", "author_or_publisher": "…", "url": "…", "page_file": "pages/001.txt",
 "location": "chapter / volume / paragraph or page number if shown",
 "grade": "A|B|C", "kind": "primary_record|translation_of_primary|scholarship|archaeology|museum|encyclopedia|news|other",
 "reports": "who states this (e.g. 'Toàn thư', 'Nguyên sử', 'Viện Khảo cổ học')",
 "legend": false, "conflicts_with": [], "notes": ""}
```

### `summary.md`, in Vietnamese, short:

- what each topic has (number of claims, best grade);
- the conflicts you found, in plain words: who says what;
- the gaps: topics with no grade A/B source;
- sources you could not open (paywall, scan only), so the owner can upload them.

Aim for 60–150 claims. Quality over quantity: one verbatim grade-A quote beats five grade-C ones.
When you are done, reply with the single word DONE.

## Tools

**Do not run any shell or terminal command** (no `ls`, no `curl`, nothing): they are denied in this run. Use only
your built-in `search_web` tool, your built-in URL-reading tool, and your file read/write tools. **Never call MCP tools** (no perplexity or any other MCP server): they are denied too, and one denied call ends the whole run. The folder `pages/` already exists.
