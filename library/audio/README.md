# Audio library (music + SFX, shared by every video)

- `index.json`: every file with `id`, `file`, `kind` (`music` | `sfx`), `mood` (music: `opening`, `tension`, `battle`,
  `ending`), `tags` (sfx: `sword`, `drum`, `water`, `oar`, `march`, `hammer`, `wind`), `license`, `added`.
- `music/`, `sfx/`: the files (mp3 or wav).
- Only files whose licence allows **monetised YouTube**. Add them with the tool, never by hand: it refuses an empty
  licence, other formats and duplicate ids, and writes a line to `LICENSES.md`.

```
.venv/bin/python -m tools.longform.audio_lib add ~/Downloads/drums.mp3 music battle-drums-01 \
    --license "YouTube Audio Library, no attribution required <URL>" --mood battle
.venv/bin/python -m tools.longform.audio_lib add ~/Downloads/sword.wav sfx sword-01 --license "..." --tags sword
.venv/bin/python -m tools.longform.audio_lib check     # missing files, missing licences
```

Music plays per chapter and is lowered under the voice automatically; SFX are light, under the voice, anchored to
sentences. A missing audio library never blocks a render (Studio shows a warning).
