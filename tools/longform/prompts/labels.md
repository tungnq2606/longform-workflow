# On-screen labels in $lang_name for "$title"

You write the short texts shown on screen (dates, names, place labels, card titles) for viewers who speak
$lang_name. `labels.json` in this folder maps each label id to its Vietnamese text.

Rules:
1. Write each label for a native $lang_name viewer: natural, short (at most 60 characters), no explanations.
2. Names and places: use exactly the form in `glossary.json` when the name is there.
3. Dates and numbers: keep every number exactly; use the local date style.
4. Add nothing that is not in the Vietnamese label.
5. **Do not run shell commands and never call MCP tools.** Use only your file read/write tools.

Write `result.json` in this folder: one key per label id in `labels.json`, every id exactly once:

```json
{"date_1288": "…", "name_thd": "…"}
```

When you are done, reply with the single word DONE.
