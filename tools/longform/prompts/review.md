# Review the script for "$title"

You are the reviewer (agy wrote this draft; you did not). Read `script.json`, `facts.json` and `style.md` in this
folder. Each fact's page is in this folder at its `page_file` if you need to re-read a quote. Do not read or write
anywhere else.

Check every sentence:
1. Each event, number, name or date is backed by the listed facts, and says no more than the facts say.
2. Numbers: write them as digits; each number must appear in a linked fact; one grade-A fact or two grade-B facts
   from different sources; otherwise reword without the number.
3. Legend → "tương truyền"; debated → "có ý kiến cho rằng"; archaeology → "cho thấy", never "chứng minh".
4. Conflicting records: both versions in plain words, who wrote what; 1–3 places per video at most.
5. Voice: every rule in `style.md`.
6. Flow: a hook question first, a new question every 60–90 seconds, an archaeological or "what is left today" ending.

Rewrite sentences in place to fix problems. You may remove facts from a sentence or drop sentences; never add a fact
id that is not in `facts.json`, and never add a fact that no fact states. Keep beat ids (B01…) as they are; new
sentences get new ids after the highest one.

Write `result.json` in this folder with the Write tool, and do nothing else: the full revised script in the same
shape as `script.json`, plus `"notes": [{"sentence": "s012", "note": "what you changed and why, in Vietnamese"}]`.
