# Review the $lang_name ($lang) script for "$title"

You are the reviewer (agy wrote this $lang_name script from the outline; you did not). Read `script.json`,
`outline.json`, `glossary.json`, `style.md`, `GUIDE.md` and `check.json` in this folder. Do not read or write anywhere
else.

Check every sentence:
1. Each event, number, name or date is backed by the facts of **its own beat** in `outline.json` (claim and verbatim
   quote), and says no more than those facts say. A fact listed for another beat is not allowed in this beat.
2. Numbers: digits, and each number appears in a linked fact.
3. Certainty words of `GUIDE.md` §6: legend, debated, archaeology ("suggests", never "proves").
4. Names exactly as in `glossary.json`. A row with `checked: false` is a proposal: if you have reason to think the
   form is wrong, flag it; do not invent a new form.
5. Voice: every rule in `style.md`; it must read as written natively in $lang_name, not translated.
6. Fix every problem listed in `check.json` (red sentences, glossary misses).

Rewrite sentences in place to fix problems. You may remove facts from a sentence or drop sentences; never add a fact id
that is not listed for that beat, and never add a fact that no fact states. Keep the beat ids and chapter ids exactly;
new sentences get new ids after the highest one.

Flag what you cannot fix or what the owner should decide (a name form, a joke that may not land, a sentence you are
unsure of). For each flag give a Vietnamese back-translation of the $lang_name sentence, so the owner (who reads
Vietnamese) can judge it.

Write `result.json` in this folder with the Write tool, and do nothing else: the full revised script in the same shape
as `script.json`, plus

```json
"flags": [{"sentence": "s012", "issue": "what the owner should decide, in Vietnamese", "back_translation_vi": "…"}]
```

An empty `flags` list means you found nothing left for the owner.
