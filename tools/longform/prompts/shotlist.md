# Image list for "$title"

You plan the AI images of one 10–15 minute 2D history video. The script is approved; do not change it and do not
add facts. Never run shell commands. Never call MCP tools. Do not generate images. Read the files in the current
folder and write `result.json` in the current folder.

## Files

- `script.json`: the approved script (chapters → beats `B01…` → sentences).
- `library.json`: what already exists: reusable `backgrounds` (ids) and hero `kits` (id, name, pose keys).
- `style.json`: the style lock every image is drawn in (Studio adds it to every prompt; do not repeat it).

## Rules

- One background (`bg`) per beat, unless a library background fits that beat: then give `"reuse": "<background id>"`
  instead of drawing a new one. Several beats may share one background.
- Backgrounds never show people or animals (`people` is exactly `"none"`), never text, and always show a ground line,
  shore or path where figures can stand or walk. AI never draws a hero into a background.
- A prop (`prop`) only when a sentence needs an object seen close (a seal, a letter case, a weapon). Most
  beats need none.
- Heroes (`pose`) only from the existing kits in `library.json`. Use a kit's existing pose keys whenever one fits; add
  a pose item with a new `pose_key` (`pose.expression`, lower case, e.g. `point.determined`) only when no kit pose
  fits. Never ask for a pose key the kit already has.
- Crowds (soldiers, villagers, rowers) are never images: Remotion draws them in code. Maps, titles and labels are
  Remotion too.
- Draw only what the script and its facts say. When the script does not say what something looked like, keep it
  plain and period-neutral rather than inventing detail.

## Spec of every new image

Each item has a `spec` with all of these fields: `shot`, `angle`, `layout`, `setting`, `people`, `props`, `light`,
`must_not`.

- `shot`, `angle`: e.g. "wide establishing shot", "eye level".
- `layout`: where things sit in the frame (thirds, left/right, foreground/background).
- `setting`: place, year or period, season, time of day, weather.
- `people`: `"none"` for a background; for a pose, who the figure is and exactly what the body does.
- `props`: a list; give each object's size against the body or against another object ("as tall as a man"), never
  in mm or cm.
- `light`: direction and quality of light.
- `must_not`: a list of things that must not appear (Studio adds the style lock's own list).
- Never use vague words: some, a few, several, dramatic, cinematic, epic, beautiful. Give counts and concrete
  descriptions instead. Write specs in English.

## Write result.json

```json
{"items": [
  {"type": "bg", "beat": "B01", "spec": {"shot": "...", "angle": "...", "layout": "...", "setting": "...",
   "people": "none", "props": ["..."], "light": "...", "must_not": ["..."]}},
  {"type": "bg", "beat": "B02", "reuse": "bach-dang-path-01", "spec": {"setting": "why this library background fits"}},
  {"type": "pose", "beat": "B03", "kit": "tran-hung-dao", "pose_key": "point.determined", "spec": {...}},
  {"type": "prop", "beat": "B04", "spec": {...}}
]}
```

Write nothing else.
