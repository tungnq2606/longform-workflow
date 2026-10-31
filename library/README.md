# Library (shared by every video and every language)

- `characters/<id>/`: hero kits. `kit.json` + transparent PNGs (one per `pose.expression`, optional blink image), model sheet. Only kit images may appear in scenes (`python -m tools.longform.kit validate <id>`).
- `backgrounds/`: reusable AI backgrounds (no people, no text), each with a `.json` sidecar: `horizonY`, `groundY`, `path` points for walking crowds.
- `crowds/`: crowd faction definitions for the code-drawn stick figures (helmet, tunic colour, weapon).
- `style/`: style locks (`longform_v1.json`): background and character prompt blocks, negative list, chroma colour, owner verdict.
- `glossary/<code>.json`: history terms and proper-name spellings/pronunciations per language (e.g. Trần Hưng Đạo in Japanese).
- `stylebook/<code>.md`: writing-style rules per language, including rules the owner kept from chat edits.
