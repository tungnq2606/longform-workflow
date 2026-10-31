# Localization guide (agy, per-language rewrite)

Sources of this guide (searched 2026-11-01 for skill names or descriptions containing `locali`, `translat`,
`transcreat`): `~/.claude/skills`, `~/.claude/plugins/cache/**/skills`, `~/.gemini/antigravity-cli/builtin`,
`~/.gemini/**/skills`. Found no localization, translation or transcreation skill (the only hits used the words in
passing: caveman-explore "localization" of code, stakeholder-update "translating progress"). So this guide is
written fresh, from the Vietnamese style book (`library/stylebook/vi.json`), the script rules
(`tools/longform/prompts/draft.md`) and the design spec §4.4 and §4.7.

## 1. Transcreation, not translation

You write the voice-over of a history video **natively** in the target language, for a viewer of that country who
does not know Vietnam. You never see the Vietnamese sentences, and you must not try to reconstruct them. You get,
per beat (scene): its goal and its facts (claim + verbatim quote). Write what a good storyteller of that country
would say about those facts.

## 2. Per beat

- Keep every beat, with its id, in the same order. Never merge, split, drop or add beats.
- Keep the beat's goal (hook, question, reveal, joke, ending…) and use its facts. Use **only** the facts listed for
  that beat: a fact from another beat is forbidden, even if it is true.
- Sentence count is free (usually 2–6 per beat). Short sentences, one idea each.
- New hooks and jokes that work in the target culture are welcome. No puns that only work in Vietnamese, no jokes
  that bend a fact.
- Every sentence that states an event, number, name or date lists the fact ids it uses in `facts`.

## 3. Context a foreign viewer lacks

A viewer abroad may not know where Đại Việt was, who the Trần were, or what the Yuan dynasty was. Explain it in a
few words **only with the beat's facts**. If no fact of the beat says it, do not explain it: say less rather than
add something.

## 4. Names

- Write every name exactly as in `glossary.json` (`target`). A row with `checked: false` is still the form to use;
  the reviewer checks it.
- The first mention may get a short gloss ("Tran Hung Dao, the Trần prince who led the defence") only if a fact of
  that beat says it.
- A name missing from the glossary: write the usual romanised form (ja: katakana) and add a `note` on the sentence
  "glossary: <Vietnamese form> → <your form>".

## 5. Numbers, dates, units

- Numbers as digits (1288, 400), and only numbers that appear in the linked facts' claims or quotes.
- Round numbers are fine for speech only if the fact gives the round number; otherwise keep the fact's number.
- Dates and units in the local format (en: "April 1288"; ja: 1288年4月; de: "April 1288"; es: "abril de 1288").
  Never convert a unit if the fact does not give the converted value.

## 6. Certainty words (spec §4.4, every language)

| Vietnamese | en | ja | de | es |
|---|---|---|---|---|
| tương truyền (legend) | legend says | 伝説によると | der Legende nach | según la leyenda |
| có ý kiến cho rằng (debated) | some historians think | 〜という説もあります | manche Historiker meinen | algunos historiadores creen |
| cho thấy (archaeology) | suggests | 示しています | deutet darauf hin | sugiere |
| never "chứng minh" | never "proves" | never 証明 | never "beweist" | never "demuestra" |

A legend fact must carry the legend words in the sentence that uses it.

## 7. Records that disagree

Tell both versions in plain words, who wrote what ("the Trần court chronicle says…, while the Yuan history
records…"), as an open question. Never explain why they differ unless a fact says why.

## 8. Never

- Never say a modern source in the voice-over (author, paper, museum, website, URL).
- Never add a fact, number, name, cause or date that the beat's facts do not state.
- No English slang in languages other than English; no slang the voice engine will misread.
- Never address viewers as a group "we/us" in a lecturing way; talk to "you" (see the per-language notes).

## 9. Per-language notes

### en
- US spelling; contractions are fine ("it's", "didn't").
- Address the viewer as "you". Light, dry humour.

### ja
- です/ます narration, short sentences (about 40 characters at most).
- Do not overload katakana slang; plain words a teenager understands.
- Names from the glossary in katakana with ・ between parts; kanji (元朝, 大越) only where the glossary gives them.
- Numbers as Arabic digits (1288年).

### de
- Address the viewer with "du" (lower case in running text), never "Sie".
- Avoid long compound nouns; split them into two words or a short phrase.
- Numbers as digits; dates "April 1288".

### es
- Neutral Latin-American Spanish, "tú" for the viewer, no "vosotros".
- Avoid regional slang from one country.

## 10. Output

The same shape as the source script: `{"lang", "chapters": [{"id", "title", "beats": [{"id", "goal",
"sentences": [{"id", "text", "facts", "kind", "note"}]}]}]}`. Chapter ids and beat ids exactly as in the outline;
chapter titles written in the target language; sentence ids s001… numbered across the whole script.
