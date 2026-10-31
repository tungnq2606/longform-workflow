# Write the $lang_name ($lang) YouTube upload texts for "$title"

You write the title, description and tags of a history video for $lang_name viewers. Read `script.json` (the
approved $lang_name voice-over), `chapters.json` (chapter titles and start times) and `sources.json` (names of the
sources behind the facts) in this folder. Do not read or write anywhere else.

## Rules

1. Title: at most 100 characters, a real question or a strong hook from the script; no clickbait that the script does
   not deliver; no fact the script does not state.
2. Description: 2–4 short paragraphs in $lang_name about what the video tells, using only what the script says.
   Do not add chapter lines: Studio appends the chapters itself.
3. The description has **exactly one** sources line, its own line, starting with `$sources_prefix`, then the source
   names from `sources.json` (short names, comma-separated). No links, no URLs, no authors' handles.
4. Never write any line saying the video is illustrated, made or generated with AI. (The owner sets the YouTube
   "altered or synthetic content" setting instead.)
5. Tags: 10–20 tags in $lang_name (plus English names where viewers search them), all tags together at most 500
   characters.
6. **Do not run shell commands and never call MCP tools.** Use only your file read/write tools, only in this folder.

## Output

Write `result.json` in this folder:

```json
{"title": "…", "description": "…\n\n$sources_prefix …", "tags": ["…"]}
```

When you are done, reply with the single word DONE.
