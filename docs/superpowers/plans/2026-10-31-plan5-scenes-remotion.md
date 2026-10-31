# Plan 5: Scene board + production Remotion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn an approved script plus approved images into a full 1440p video per language.
- Claude writes a beat-keyed scene file: background camera, heroes, crowds, cards, map, sound.
- Studio shows it as a scene board with previews.
- Voice timing comes from the owner's mp3 files.
- One Remotion composition renders any language: voice, chapter music with ducking, light SFX, subtitles (.srt) and chapters.

**Architecture:**
- **Scenes** are keyed by beat, not by sentence (spec §4.6–4.7): `projects/<id>/scenes/scenes.json`.
- **Timing per language** (`lang/<code>/timing.json`) is computed from voice parts by pause detection. Remotion's bundled ffmpeg (`npx remotion ffmpeg`) decodes the mp3 files; there is no new system dependency.
- **Composition.** One composition, `Longform`, gets `{scenes, timing, lang, audio, labels}` as props. Its duration comes from the timing (`calculateMetadata`).
- **Assets.** The render stages only the files it needs, as in Plan 1.
- **Map.** Natural Earth coastlines (public domain) are cropped to a Vietnam / South China box and drawn by code.
- **Music and SFX** come from a licensed library the owner fills (`library/audio/`). Missing audio never blocks a render; it shows as a warning.

**Tech Stack:** Python 3.9 + Pillow; Remotion 4.0.537 (`tools/anim`); existing components `Crowd`, `Hero`, `Title`, `path.ts`; Plan 2–4 modules; `claude -p` for scene writing (Claude does Remotion, owner 2026-10-31).

**Spec:** `docs/superpowers/specs/2026-10-31-longform-workflow-design.md` §3, §4.6, §4.7 (beat unit, timing per language), §4.8 (music + SFX), §5 (map decision) · Plans 1–4

## Global Constraints

- All constraints of Plans 2–4 hold.
- Output is 2560x1440, 30 fps, H.264 ~16 Mbps (`remotion.config.ts`), AAC 48 kHz. Keep only the final file per language.
- **On-screen text** all comes from Remotion, in the render language: chapter titles, dates, name labels, the two-source card, map labels and the "bản đồ hiện đại" note. Text inside AI images is never relied on.
- **Heroes** only through `<Hero image="kit/pose">` (`HeroKey` type). The scene validator refuses unknown kit poses before render, and `render.type_check()` runs before every render (Plan 1 fix).
- **Map:**
  - coastline from Natural Earth (public domain), recorded in `LICENSES.md`;
  - a small note "Bản đồ hiện đại" (per language) whenever a map is shown;
  - historical borders only when the scene names a fact id that describes them; otherwise only places, arrows and approximate shaded areas.
- **Audio:**
  - music per chapter (opening, tension, battle, ending), automatically lowered under the voice;
  - SFX light and under the voice, anchored to sentences, so they follow each language's timing;
  - every audio file in `library/audio/index.json` has a `license` field, and is listed in `LICENSES.md`;
  - files without a licence are refused.
- Claude workers run inside their run folder only (no `--add-dir`); every input is copied in (Plan 3 fix).
- Tests: `.venv/bin/python -m unittest discover -s tools/longform/tests -v`, `node --test studio/static/`, `cd tools/anim && node --test src/longform/ && npx tsc --noEmit -p .`
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A voice part has fewer clear pauses than sentence boundaries** (fast speaker). Timing still assigns every sentence a start, falling back to proportional split by character count, and marks that part `approx: true` (Task 2, `test_too_few_pauses_falls_back`).
2. **A scene names a kit pose, background, audio id or fact that does not exist.** The validator refuses the scene file with a Vietnamese message before any render (Task 3, `test_validator_unknown_refs`).
3. **A language whose voice is longer or shorter than Vietnamese.** The beat durations follow that language's timing, and the hero key changes still land on the right sentence (Task 4, `timeline.test.ts` `scales with language timing`).
4. **Music ducking.** Volume is lowered (≤ 0.25) during any sentence and back up (≤ 0.6) in gaps longer than 1.5 s, with a 0.3 s ramp: no jumps (Task 4, `ducking.test.ts`).
5. **A render while voice parts are missing.** The render is refused with "thiếu giọng phần N" and never produces a silent video (Task 6, `test_render_refuses_missing_voice`).

---

### Task 1: Audio library + licences

**Files:**
- Create: `library/audio/index.json` (`{"music": [], "sfx": []}`), `library/audio/README.md`, `LICENSES.md` (fonts, Remotion, Real-ESRGAN, Natural Earth, audio section), `tools/longform/audio_lib.py`
- Test: `tools/longform/tests/test_audio_lib.py`

**Interfaces:**
- Produces:
  - Entry: `{"id": "battle-drums-01", "file": "music/battle-drums-01.mp3", "kind": "music|sfx", "mood": "opening|tension|battle|ending" (music), "tags": ["sword", "drum", "water", "oar", "march", "hammer", "wind"] (sfx), "license": "text + URL", "added"}`.
  - `audio_lib.load() -> dict`.
  - `audio_lib.add(path, kind, id, license, mood=None, tags=()) -> dict`:
    - copies the file into `library/audio/<kind>/`;
    - refuses an empty licence, a non-mp3/wav file, or a duplicate id;
    - appends a line to `LICENSES.md`.
  - `audio_lib.problems() -> list[str]`: files that are missing, or that have no licence.
  - `audio_lib.by_mood(mood) -> list` and `audio_lib.by_tag(tag) -> list`.
  - When the library is empty, Studio shows inbox item `audio_missing` (once, key `audio:empty`): "Thư viện nhạc/hiệu ứng trống: thêm file có giấy phép YouTube kiếm tiền".
- [ ] Steps: failing tests (`test_add_requires_license`, `test_add_copies_and_logs_license`, `test_problems_missing_file`, `test_by_mood_and_tag`), then run, implement, run, commit `feat: licensed audio library`.

---

### Task 2: Voice timing per language

**Files:**
- Create: `tools/longform/timing.py`
- Test: `tools/longform/tests/test_timing.py`

**Interfaces:**
- Consumes (written by Plan 6): `lang/<code>/audio/parts.json` = `[{"part": "01", "file": "01.mp3", "sentences": ["s001", ...]}]`, plus the mp3 files next to it.
- Produces:
  - `timing.decode(mp3, wav)`: runs `npx remotion ffmpeg -y -i <mp3> -ac 1 -ar 16000 <wav>` in `tools/anim`.
  - `timing.pauses(wav, thr_ratio=0.06, min_ms=150) -> (list[(start, end)], duration)`: a port of `tools/kit/storyboard.py pauses`, stdlib `wave`.
  - `timing.split_part(pauses, duration, sentences: list[(id, text)]) -> list[{"id", "start", "end"}]`:
    - takes the `len(sentences)-1` longest pauses, kept in time order, as the boundaries;
    - when there are too few pauses, it splits proportionally by character count and marks the part `approx`.
  - `timing.build(pdir, lang) -> dict`:
    - places the parts one after another with `GAP = 0.4` s;
    - writes `lang/<code>/timing.json` `{"lang", "duration", "beats": [{"id", "start", "end", "sentences": [...]}], "parts": [{"part", "start", "duration", "approx"}]}`;
    - a sentence's beat comes from that language's script (`lang/<code>/script/script.json`, or `script/script.json` for the source language);
    - sets `progress.set_lang(pdir, lang, "voice", "done")`.
  - `timing.missing_parts(pdir, lang) -> list[str]`.
- [ ] Steps: failing tests. Synthesize WAV fixtures with tone and silence in Python, and patch `decode` to copy the WAV.
  - `test_pauses_found`
  - `test_split_by_longest_pauses`
  - `test_too_few_pauses_falls_back`
  - `test_build_beats_and_gap`
  - `test_missing_parts`
- Then run, implement, run, commit `feat: voice timing per language from pauses`.

---

### Task 3: Scene file, validator, Claude scene writer

**Files:**
- Create: `tools/longform/scenes.py`, `tools/longform/prompts/scenes.md`
- Modify: `tools/longform/workers.py` (kind `claude_scenes`)
- Test: `tools/longform/tests/test_scenes.py`

**Interfaces:**
- Produces:
  - `scenes/scenes.json`:
    - Top level: `{"version", "chapters": [{"id": "C01", "music": "audio id"|null, "title_card": true}], "beats": {"B01": {...}}}`.
    - Each beat:
      - `"background": {"id": "library:<id>"|"project:<item id>", "camera": {"from": {"zoom": 1, "x": 0, "y": 0}, "to": {...}}}`;
      - `"heroes": [{"key": "kit/pose", "x": 0-2560, "enter": "left|right|none", "keys": [{"sentence": "s003", "key": "kit/pose"}]}]`;
      - `"crowds": [{"faction", "count", "path": "background"|[[x, y], ...], "speed"}]`;
      - `"cards": [{"type": "date|name|two_source|chapter", "sentence": "s002", "text_key": "label id"}]`;
      - `"map": null | {"bbox": [lon0, lat0, lon1, lat1], "places": [{"label_key", "lon", "lat"}], "arrows": [{"from": [lon, lat], "to": [lon, lat], "sentence"}], "areas": [{"points": [[lon, lat], ...], "fact": "F012"|null}]}`;
      - `"sfx": [{"sentence": "s004", "id": "sword-01", "offset": 0.3, "gain": 0.4}]`.
  - `scenes/labels.json`: `{"<label id>": {"vi": "...", "en": "...", ...}}`. All on-screen text, per language, filled by the scene writer for vi and by Plan 6 for other languages.
  - `scenes.validate(pdir, data) -> list[str]` (Vietnamese). It refuses:
    - beats not in the approved script, and script beats with no scene;
    - unknown `kit/pose` (from the kit json files);
    - unknown backgrounds (library or an approved project item);
    - unknown audio ids;
    - unknown fact ids on map areas, and an `areas` entry with `fact: null` that claims a border (type `border`);
    - unknown sentence ids;
    - labels without a vi text.
  - `scenes.save(pdir, data, by)`: versioned like `script.save`, with a lock.
  - Job kind `claude_scenes`, lane `claude`, params `{"project"}`:
    - `build` refuses unless the script is approved and at least one image is approved;
    - the run folder holds the script, approved image list with thumbnails, kits, `library_index.summary()`, audio index, and the timing (if present);
    - `prompts/scenes.md` describes the schema, the simple-motion rules (spec §4.6), sound rules (light, under the voice, 0–3 SFX per beat) and the map rules;
    - `on_end` runs `validate`, then `save`, then `progress.set_step(scenes, "wait")`, then inbox `scenes_ready`.
- [ ] Steps: failing tests.
  - `test_validator_unknown_refs`
  - `test_validator_missing_beat`
  - `test_border_needs_fact`
  - `test_save_versions`
  - `test_claude_scenes_requires_approved_script`
  - `test_claude_scenes_on_end_validates`
- Then run, implement, run, commit `feat: beat-keyed scene file with validator and Claude scene writer`.

---

### Task 4: Production composition (timeline, camera, cards, audio)

**Files:**
- Create in `tools/anim/src/longform/`:
  - `timeline.ts` + `timeline.test.ts`;
  - `ducking.ts` + `ducking.test.ts`;
  - `Longform.tsx`, `Scene.tsx`, `Cards.tsx` (`DateCard`, `NameLabel`, `TwoSourceCard`, `ChapterCard`), `SoundTrack.tsx`
- Modify: `tools/anim/src/Root.tsx` (register `Longform`, 2560x1440, 30 fps, `calculateMetadata` from props)

**Interfaces:**
- Produces:
  - `timeline.build(scenes, timing, fps) -> {durationInFrames, beats: [{id, from, durationInFrames, sentences: [{id, from}]}]}`. Frames come from the timing seconds, plus a 15-frame tail.
  - `timeline.sentenceFrame(tl, sentenceId) -> number`.
  - `ducking.volumeAt(t, sentences: [{start, end}], {low: 0.22, high: 0.55, ramp: 0.3, gap: 1.5}) -> number`.
  - `camera(t01, from, to)`: eased zoom/pan.
  - `<Longform scenes timing labels lang audio />`:
    - beats as `<Sequence>`;
    - each beat is a `<Scene>` with the background `Img` under the camera, `Crowd`s, `Hero`s (with `keys` at sentence frames), cards at their sentence frame, and `MapView` when set;
    - `<SoundTrack>`: the voice parts at their timing starts, chapter music with `volume={(f) => volumeAt(...)}`, and SFX at sentence frame + offset with their gain.
  - Fonts come from `languages.json` (`Be Vietnam Pro`, or `Noto Sans JP` from Plan 6) via `FontFace` and `staticFile`, with `.catch(cancelRender)`. This also fixes the Plan 1 Title minor.
- [ ] Steps: failing `node --test` cases.
  - `timeline.test.ts`: `beat frames follow timing`, `scales with language timing`, `sentenceFrame`.
  - `ducking.test.ts`: `low during speech`, `high in long gap`, `no jump`.
- Then run, implement, run (`npx tsc --noEmit -p .` must pass), commit `feat: Longform composition with timeline, cards and ducked sound`.

---

### Task 5: Map from Natural Earth

**Files:**
- Download (untrusted, into its own new folder `tools/maps/vendor/`, gitignored): `ne_10m_coastline.geojson` and `ne_10m_land.geojson` from `https://github.com/nvkelso/natural-earth-vector` (`geojson/` folder, public domain). Record the URL and SHA-256 in `LICENSES.md`.
- Create: `tools/longform/mapdata.py` (crop + simplify), `library/maps/vn_region.json` (output, committed, small), `tools/anim/src/longform/geo.ts` + `geo.test.ts`, `tools/anim/src/longform/MapView.tsx`

**Interfaces:**
- Produces:
  - `mapdata.crop(geojson_path, bbox=(100, 7, 125, 26), tolerance=0.01) -> dict`:
    - clips lines and polygons to the bbox;
    - Douglas–Peucker simplification (pure Python);
    - output `{"bbox", "coast": [[[lon, lat], ...]], "land": [[[lon, lat], ...]]}`, under 400 KB.
  - `geo.project([lon, lat], bbox, w, h) -> [x, y]` (equirectangular with cos(lat) correction).
  - `geo.pathD(points, ...) -> string`.
  - `<MapView map labels lang at />`:
    - land fill with a paper texture tint, and the coast stroke drawn on over 20 frames;
    - places as dots with labels (`labels[label_key][lang]`);
    - arrows drawn with an animated dash at their sentence frame;
    - areas as hatched fill;
    - a bottom-right note `labels.modern_map[lang]` ("Bản đồ hiện đại", "Modern map", "現代の地図", "Heutige Karte", "Mapa actual").
- [ ] Steps: failing tests.
  - Python: `test_crop_keeps_bbox`, `test_simplify_reduces_points`.
  - TS: `geo.test.ts` `project corners`, `pathD`.
- Then download, check the hash, run `crop`, implement, run, commit `feat: Natural Earth map component`.

---

### Task 6: Render per language, previews, subtitles, chapters

**Files:**
- Modify: `tools/longform/render.py`, `tools/longform/workers.py`
- Test: `tools/longform/tests/test_render.py` (new cases)

**Interfaces:**
- Produces:
  - `render.assets(pdir, lang) -> list[str]` (workspace-relative files to stage): backgrounds used, kit folders used, project final images used, voice parts, audio files used, fonts, `library/maps/vn_region.json`.
  - `render.props(pdir, lang) -> dict`: `{scenes, timing, labels, lang, audio: {voice: [...], music: {...}, sfx: [...]}}`, with paths relative to the staged public folder.
  - `render.render_lang(pdir, lang) -> str`:
    - refuses with `ValueError` when parts are missing ("thiếu giọng phần N"), the timing is missing, or `scenes.validate` reports problems;
    - runs `type_check()`, stages the assets, renders `Longform` to `lang/<code>/render/<pid>_<code>_1440p.mp4`;
    - writes `<pid>_<code>.srt` (one cue per sentence from the timing; text from that language's script) and `chapters.txt` (`0:00 Title` lines from chapter start times, first at 0:00);
    - sets `progress.set_lang(pdir, lang, "render", "done")`.
  - `render.still_beat(pdir, beat, lang="vi") -> str`: `images/previews/<beat>.png`, a frame in the middle of the beat (`npx remotion still`).
  - Job kinds:
    - `render_lang` (lane `render`, params `{"project", "lang"}`; on success an inbox item `render_done` "Đã render <LANG>" with the file path, no Telegram spam: one message per language);
    - `render_still` (lane `render`).
- [ ] Steps: failing tests.
  - `test_render_refuses_missing_voice`
  - `test_srt_from_timing`
  - `test_chapters_start_at_zero`
  - `test_assets_only_used_files`
  - `test_props_paths_relative`
- Then run, implement, run, commit `feat: per-language render with subtitles, chapters and beat previews`.

---

### Task 7: Scene board UI

**Files:**
- Create: `studio/static/scenes_view.js`
- Modify: `studio/server.py` (routes), `app.js`, `lib.js`, `style.css`, `lib.test.js`
- Test: new `test_server.py` cases plus lib tests

**Interfaces:**
- API:
  - `GET /api/projects/<id>/scenes` → `{scenes, problems, labels, previews: {beat: bool}, timing: {lang: bool}}`;
  - `POST …/scenes/write` → the `claude_scenes` job;
  - `POST …/scenes/beat/<B>` `{"sfx": [...], "music": ...}` (the owner edits sound; validated);
  - `POST …/scenes/preview/<B>` → the `render_still` job;
  - `GET …/scenes/preview/<B>` → the PNG;
  - `POST …/render/<lang>` → the `render_lang` job;
  - `GET /api/audio` → the audio index.
- UI (`#/p/<id>/scenes`), mounted with its own poll:
  - A table, one row per beat:
    - the beat id and goal;
    - the source sentences (short);
    - a background thumbnail;
    - heroes (kit/pose chips);
    - crowds;
    - motion (camera from → to);
    - sound (SFX chips with ✕, plus "+" picking from the audio index by tag);
    - status (problems in red);
    - preview (thumbnail, or "Xem trước" which queues a still).
  - Top bar:
    - "Claude dựng cảnh";
    - the problems count;
    - a render button per language with its state (timing missing, ready, rendering, done with the file path);
    - a warning when the audio library is empty.
- [ ] Steps: failing tests.
  - `test_scenes_endpoint`
  - `test_beat_sound_edit_validated`
  - `test_preview_route_only_known_beats`
  - lib `beatStatus`, `sfxChips`
- Then run, implement, run. Take screenshots with a fixture root on port 8799 (light, dark, 500 px) and fix what is broken. Commit `feat: Studio scene board`.
