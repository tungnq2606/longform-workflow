# Write the scene file for "$title"

You build the scenes of a 2D history video in Remotion terms. Everything you need is in this folder; do not read or
write anywhere else, and do not run commands.

Inputs:
- `script.json`: the approved script (chapters → beats → sentences). Beat ids (B01…) are the unit: one scene per beat.
- `images.json`: approved images of this project (`thumbs/` has a small preview of each; look at them). Backgrounds
  are `bg` items; hero poses are already in the kits.
- `kits.json`: hero kits and their poses. A hero key is `<kit id>/<pose>` exactly as listed, e.g. `tran-hung-dao/stand.calm`.
- `library.json`: reusable backgrounds (`library:<id>`); `has_path` says whether crowds can walk its path.
- `audio.json`: licensed music (`mood`) and sound effects (`tags`). Use only these ids.
- `facts.json`: checked facts (id + claim), for map areas and borders.
- `labels.json`: on-screen texts already written; `current_scenes.json` (if present): the scene file to improve.
- `timing.json` (if present): when each sentence is spoken in Vietnamese.

Write `result.json` with the Write tool, and do nothing else:

```
{"scenes": {"chapters": [{"id": "C01", "music": "<music id>" | null, "title_card": true}],
            "beats": {"B01": {
              "background": {"id": "library:<id>" | "project:<BG item id>",
                             "camera": {"from": {"zoom": 1, "x": 0, "y": 0}, "to": {"zoom": 1.08, "x": -60, "y": 0}}},
              "heroes": [{"key": "<kit>/<pose>", "x": 1900, "enter": "right",
                          "keys": [{"sentence": "s003", "key": "<kit>/<other pose>"}]}],
              "crowds": [{"faction": "daiviet" | "nguyen", "count": 24, "path": "background", "speed": 0.0012}],
              "cards": [{"type": "date", "sentence": "s002", "text_key": "date_1288"}],
              "map": null,
              "sfx": [{"sentence": "s004", "id": "<sfx id>", "offset": 0.3, "gain": 0.35}]}}},
 "labels": {"date_1288": {"vi": "Năm 1288"}}}
```

Rules:
1. Every beat of the script has exactly one scene; no other beats. Sentence ids must belong to that beat.
2. Simple motion only (spec): camera zoom 1–1.15 and a slow pan (x, y within ±200 px) per beat; heroes breathe and
   blink by themselves, change pose on a sentence (`keys`), slide in from the side (`enter`); crowds walk a path
   (`"background"` only when `has_path` is true, otherwise a list of [x, y] points on the 2560x1440 frame), count
   1–80, speed 0.0005–0.002.
3. A hero only through a kit key listed in `kits.json`; never invent a pose. A beat with no fitting pose has no hero.
4. Cards (`date`, `name`, `two_source`, `chapter`) show on their sentence. Their text comes from `labels`, written in
   Vietnamese (`vi`) only, short, and only what the script sentence says: never a new fact, number or name.
   `two_source` needs `text_key` (one record) and `text_key2` (the other record).
5. Map (`map`): `bbox` [lon0, lat0, lon1, lat1] inside 100–125 E, 7–26 N; `places` with a `label_key`; `arrows`
   `{"from": [lon, lat], "to": [lon, lat], "sentence"}` for movements the script states; `areas` are approximate shaded
   areas `{"points": [[lon, lat], ...], "fact": null, "type": "area"}`. A historical border (`"type": "border"`) only
   when a fact in `facts.json` describes it, with that fact id. Places and arrows only where the script says so.
6. Sound is light and under the voice: one music id per chapter by mood (opening, tension, battle, ending) or null;
   0–3 sound effects per beat on the sentence that shows the thing (sword, drum, water, oar, march, hammer, wind),
   gain 0.2–0.5, offset in seconds after the sentence starts. Leave sound out rather than guess.
7. No text inside images is ever relied on; every on-screen word is a label.
