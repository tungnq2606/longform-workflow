# Plan 1: Foundation + 10-second spike — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean the workspace down to the long-form workflow, lay the project/library/language structure, and render a 10-second Remotion spike (AI background + code-drawn marching crowd + AI-drawn hero kit + Remotion text) that the owner approves as the style lock for every later plan.

**Architecture:** Python tools live in a new package `tools/longform/` (stdlib + Pillow, unittest). Remotion work lives in `tools/anim/src/longform/` (pure math in `.ts` tested with `node --test`, components in `.tsx`). Hero kits are folders in `library/characters/<id>/` with a `kit.json`; a generator writes `kits.generated.ts` so an unknown pose is a TypeScript error. Each project renders from its own staged `public/` folder so Remotion never copies the workspace.

**Tech Stack:** Python 3.9 (system) + venv with Pillow 11.3.0; Node 26 (`node --test` strips types); Remotion 4.0.537 (already in `tools/anim`); agy CLI (`~/.local/bin/agy`) for every image (gflow removed by the owner 2026-10-31).

**Spec:** `docs/superpowers/specs/2026-10-31-longform-workflow-design.md` · Roadmap: `docs/superpowers/plans/2026-10-31-longform-roadmap.md`

## Global Constraints

- Workspace root `WS = /Users/quoctung/Documents/AI/youtube-skills-workspace`; archive root `/Users/quoctung/Documents/AI/archive/2026-10-31/` (move, never delete).
- Output 2560x1440, 30 fps, H.264 ~16 Mbps, AAC 48 kHz.
- AI images: no text, no letters; backgrounds have no people; hero images on a flat chroma green `#00B140` background (never white).
- Languages for now: `vi` (source), `en`, `ja`, `de`, `es`.
- No new macOS-only calls (`sips`, Swift, `osascript`); no new `.sh` scripts.
- Never print or commit `dashboard/secrets/telegram.json`.
- Commits end with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Python tests: `.venv/bin/python -m unittest discover -s tools/longform/tests -v`. TS tests: `cd tools/anim && node --test src/longform/`.

## Review Focus

1. Vietnamese title or slug with diacritics ("Bạch Đằng 1288") → ASCII folder `001-bach-dang-1288`, not a crash or a folder with `đ` (Task 3, `test_slug_ascii`).
2. AI hero image whose clothes are white or light green-ish → clothes stay opaque; only the background key is removed (Task 4, `test_white_clothes_kept`).
3. AI image where the generator drew a slightly different green than `#00B140` → key is taken from the border pixels, not the constant (Task 4, `test_key_from_border`).
4. A scene asks for a pose the kit does not have → build fails with a message naming the kit and pose, not a blank frame at render (Task 6, `tsc` check step + `test_missing_image_file`).
5. Crowd path whose far end sits above the horizon or whose points repeat → soldiers still placed, scale clamped to `[minS, maxS]`, no NaN (Task 5, `zero-length segment` and `clamp` tests).

---

### Task 1: Git, ignore rules, Python venv

**Files:**
- Create: `.gitignore`, `requirements-longform.txt`
- Test: shell checks below

- [ ] **Step 1: Write `.gitignore`**

Ignore: `node_modules/`, `.venv/`, `tools/youtube/.venv/`, `dashboard/secrets/`, `config/secrets/`, `dashboard/jobs/`, `dashboard/agy_work/`, `tmp/`, `.superpowers/`, `*.lock`, `**/*.mp4`, `**/*.mp3`, `**/*.wav`, `projects/*/images/raw/`, `projects/*/public/`, `projects/*/render/`, `__pycache__/`, `.DS_Store`.

- [ ] **Step 2: Create venv and pin Pillow**

`requirements-longform.txt` contains exactly `Pillow==11.3.0`.
Run: `python3 -m venv .venv && .venv/bin/pip install -r requirements-longform.txt && .venv/bin/python -c "import PIL; print(PIL.__version__)"`
Expected: `11.3.0`

- [ ] **Step 3: Init repo and verify secrets are ignored**

Run: `git init && git check-ignore dashboard/secrets/telegram.json`
Expected: prints `dashboard/secrets/telegram.json`

- [ ] **Step 4: First commit**

Run: `git add -A && git status --short | grep -E "secrets|\.mp4|node_modules" ; git commit -m "chore: track workspace before long-form rebuild"`
Expected: the grep prints nothing; commit succeeds.

---

### Task 2: Archive Shorts, 3D office and legacy render code; rewrite CLAUDE.md

**Files:**
- Move to `/Users/quoctung/Documents/AI/archive/2026-10-31/workspace-code/` (keep relative paths): `tools/shorts/`, `dashboard/office/`, `dashboard/vendor/three/`, `templates/channel/`, `tools/anim/src/current.ts`, `tools/anim/src/current_frames.ts`, `tools/anim/src/kit/Video.tsx`, `tools/anim/src/kit/FramesVideo.tsx`, `tools/anim/render.sh`, `tools/anim/render_frames.sh`, `tools/anim/prep.py`, `tools/anim/prep_frames.py`
- Move to `/Users/quoctung/Documents/AI/archive/2026-10-31/skills/`: `/Users/quoctung/Documents/AI/.claude/skills/yt-packaging`, `yt-script-retention`, `yt-topic-scout`, `yt-video-pipeline`
- Modify: `dashboard/server.py:1409-1416` (remove the `/office` and `/vendor/` routes), `tools/anim/src/kit/index.ts` (drop the `Video` type re-export), `tools/anim/src/Root.tsx` (register no old compositions; Task 5 adds `Spike`)
- Rewrite: `CLAUDE.md`

Keep: `tools/kit/storyboard.py` (its `sentence_starts` is reused in Plan 5), `tools/gemini/*` (except `agy_images.py`/`auto_images.py`, archived with `tools/flowcli.py` when gflow was dropped), `tools/imageprompts/*`, `tools/research/scout.py`, `tools/notify.py`, `tools/workqueue.py`, `tools/edge-tts-batch/`, `channels/vn-history/` (until Plan 2 moves brand out), `dashboard/` (until Plan 2 replaces it).

- [ ] **Step 1: Move the folders and files** with `mv` (create parents first). Add a line per moved item to `/Users/quoctung/Documents/AI/archive/2026-10-31/README.md`.

- [ ] **Step 2: Remove the office routes** from `dashboard/server.py`; `/office` must fall through to the normal 404.

- [ ] **Step 3: Verify the old dashboard still starts**

Run: `python3 dashboard/server.py & sleep 3; curl -s -o /dev/null -w "%{http_code} " http://127.0.0.1:8765/api/state; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8765/office; kill %1`
Expected: `200 404`

- [ ] **Step 4: Rewrite `CLAUDE.md`** for the new workspace: one long-form workflow, history only, no Shorts; folder map (`projects/`, `library/`, `config/`, `tools/longform/`, `tools/anim/src/longform/`); links to the spec, the roadmap and this plan; carry over the "Rules (do not break)" that still apply (sources rule with the conflicting-records exception, never invent facts, licences, 1440p, upload settings, review thresholds, prompt standard, queue/pause rules, Telegram secret). Drop every Shorts, Veo, Median Worker and Fossil section.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "chore: archive Shorts, 3D office and legacy render code"
```

---

### Task 3: Project skeleton, library folders, language config

**Files:**
- Create: `tools/longform/__init__.py`, `tools/longform/paths.py`, `tools/longform/languages.py`, `tools/longform/project.py`, `config/languages.json`, `library/README.md` (+ empty dirs `library/characters/`, `library/backgrounds/`, `library/crowds/`, `library/style/`, `library/glossary/`, `library/stylebook/`), `projects/.keep`
- Test: `tools/longform/tests/__init__.py`, `tools/longform/tests/test_project.py`

**Interfaces:**
- Produces:
  - `paths.root() -> str` (env `LONGFORM_ROOT` overrides `WS`), `paths.projects() -> str`, `paths.library() -> str`, `paths.config() -> str`
  - `languages.Lang` dataclass: `code: str, name: str, voice_engine: str, voice: str, speed: float, font: str, line_break: str`
  - `languages.load_languages() -> dict[str, Lang]`
  - `project.ascii_slug(text: str) -> str`
  - `project.create_project(num: int, slug: str, title: str, langs: list[str]) -> str` (returns project dir)
  - `project.load_project(pdir: str) -> dict`; `project.list_projects() -> list[dict]`
  - CLI: `python -m tools.longform.project new 1 "Bạch Đằng 1288" --title "..." --lang vi,en,ja`

`config/languages.json` values:

| code | name | voice_engine | speed | font | line_break |
|---|---|---|---|---|---|
| vi | Tiếng Việt | vbee | 1.13 | Be Vietnam Pro | space |
| en | English | elevenlabs | 1.0 | Be Vietnam Pro | space |
| ja | 日本語 | elevenlabs | 1.0 | Noto Sans JP | cjk |
| de | Deutsch | elevenlabs | 1.0 | Be Vietnam Pro | space |
| es | Español | elevenlabs | 1.0 | Be Vietnam Pro | space |

`voice` is `""` for all (the owner fills it).

Project layout made by `create_project` (`NNN` zero-padded to 3):
```
projects/NNN-slug/project.json   {"id","num","slug","title","source_lang":"vi","languages":[...],"created":"YYYY-MM-DD"}
projects/NNN-slug/{research,script,images/raw,scenes,audio}/
projects/NNN-slug/lang/<code>/{script,audio,render,upload}/
```

- [ ] **Step 1: Write the failing tests** (each test sets `LONGFORM_ROOT` to a `tempfile.mkdtemp()` containing a copy of `config/languages.json`)

```python
def test_slug_ascii(self):
    self.assertEqual(project.ascii_slug("Bạch Đằng 1288!"), "bach-dang-1288")
def test_create_layout(self):
    d = project.create_project(1, "bach-dang", "Bạch Đằng", ["en", "ja"])
    self.assertTrue(d.endswith("001-bach-dang"))
    meta = project.load_project(d)
    self.assertEqual(meta["languages"], ["vi", "en", "ja"])   # source always first
    for c in ("vi", "en", "ja"):
        self.assertTrue(os.path.isdir(os.path.join(d, "lang", c, "audio")))
def test_unknown_language(self):
    with self.assertRaises(ValueError): project.create_project(2, "x", "X", ["fr"])
def test_duplicate_number(self):
    project.create_project(3, "a", "A", [])
    with self.assertRaises(FileExistsError): project.create_project(3, "b", "B", [])
def test_languages_loaded(self):
    L = languages.load_languages()
    self.assertEqual(set(L), {"vi", "en", "ja", "de", "es"})
    self.assertEqual(L["vi"].speed, 1.13); self.assertEqual(L["ja"].font, "Noto Sans JP")
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m unittest discover -s tools/longform/tests -v`
Expected: FAIL / ImportError on `tools.longform.project`

- [ ] **Step 3: Implement** `paths.py`, `languages.py`, `project.py`, `config/languages.json`, library folders and `library/README.md` (one paragraph per subfolder: what lives there). `ascii_slug` uses `unicodedata` NFD + explicit `đ/Đ → d`, lowercases, collapses non-alphanumerics to `-`. A duplicate is any existing `projects/NNN-*` with the same number.

- [ ] **Step 4: Run tests** — same command. Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/longform config library projects/.keep && git commit -m "feat: long-form project layout and language config"
```

---

### Task 4: Chroma-key cutout tool

**Files:**
- Create: `tools/longform/cutout.py`
- Test: `tools/longform/tests/test_cutout.py`

**Interfaces:**
- Produces:
  - `cutout.cut(src: str, dst: str, tol: int = 60, pad: int = 16) -> dict` → writes RGBA PNG trimmed to the opaque bbox + `pad`; returns `{"width": int, "height": int, "anchor": [x, y], "key": [r, g, b]}` where `anchor` = horizontal centre of the opaque pixels in the lowest 3% of opaque rows, `y` = last opaque row (feet).
  - `cutout.check(path: str, source: str | None = None) -> list[str]` problems: `"no transparency"`, `"key colour left on figure (N%)"` when >0.5% of opaque pixels are within `tol` of the key, `"touches edge"` when an opaque pixel is on the original image border (figure cut off).
  - CLI: `python -m tools.longform.cutout SRC DST` prints the dict as JSON.

Approach: key = median RGB of a 4-px border ring of the source; pixel distance in RGB; alpha = 0 below `tol`, ramp to 255 over `tol..tol*1.6`; despill: for semi-transparent edge pixels set `g = min(g, max(r, b))`.

- [ ] **Step 1: Write the failing tests** (images synthesised with Pillow in a temp dir)

```python
def test_white_clothes_kept(self):      # green bg, white ellipse "toga" with black outline, red rect "belt"
    info = cutout.cut(src, dst)
    im = Image.open(dst); self.assertEqual(im.mode, "RGBA")
    self.assertEqual(im.getpixel(center_of_toga)[3], 255)
    self.assertEqual(cutout.check(dst), [])
def test_key_from_border(self):         # background (20, 190, 80) instead of #00B140
    info = cutout.cut(src, dst); self.assertEqual(info["key"], [20, 190, 80])
    self.assertEqual(Image.open(dst).getpixel((0, 0))[3], 0)
def test_anchor_at_feet(self):          # figure 200 px wide centred at x=500, bottom at y=900 in a 1000x1000 source, pad 16
    info = cutout.cut(src, dst)
    self.assertAlmostEqual(info["anchor"][0], info["width"] / 2, delta=3)
    self.assertEqual(info["anchor"][1], info["height"] - 1 - 16)
def test_touches_edge(self):            # figure drawn through the bottom border
    cutout.cut(src, dst); self.assertIn("touches edge", cutout.check(dst, source=src))
```


- [ ] **Step 2: Run to verify they fail** — `.venv/bin/python -m unittest tools.longform.tests.test_cutout -v` → ImportError.
- [ ] **Step 3: Implement `cutout.py`.**
- [ ] **Step 4: Run tests** → PASS.
- [ ] **Step 5: Commit** — `git add tools/longform/cutout.py tools/longform/tests/test_cutout.py && git commit -m "feat: chroma-key cutout for hero kit images"`

---

### Task 5: Remotion crowd (code-drawn stick soldiers on a path)

**Files:**
- Create: `tools/anim/src/longform/path.ts`, `tools/anim/src/longform/path.test.ts`, `tools/anim/src/longform/Soldier.tsx`, `tools/anim/src/longform/Crowd.tsx`, `tools/anim/src/longform/factions.ts`
- Modify: `tools/anim/tsconfig.json` (add `"allowImportingTsExtensions": true`, keep `noEmit`), `tools/anim/package.json` (`"name": "longform-anim"`, script `"test": "node --test src/longform/"`)

**Interfaces:**
- Produces:
  - `type Pt = [number, number]`
  - `pointAt(path: Pt[], t: number): {x: number; y: number; angle: number}` — arc-length position, `t` clamped to `[0,1]`, zero-length segments skipped.
  - `depthScale(y: number, horizonY: number, groundY: number, minS: number, maxS: number): number` — linear from `minS` at `horizonY` to `maxS` at `groundY`, clamped.
  - `FACTIONS: Record<'daiviet' | 'nguyen', {skin: string; tunic: string; helmet: 'round' | 'cone'; weapon: 'spear' | 'sword'; shield: boolean}>` — values: daiviet `{skin:'#b9773f', tunic:'#7a4e2d', helmet:'round', weapon:'spear', shield:true}`, nguyen `{skin:'#c58a52', tunic:'#3f6b73', helmet:'cone', weapon:'sword', shield:true}` (placeholder colours; Plan 5 fixes them from sources).
  - `<Soldier x y s faction seed facing?: 1 | -1 walkPhase: number />` — round head with big white eyes and dot pupils looking in `facing` direction, mouth from seed (`flat|o|frown|smile`), stick body/limbs (ink `#2b2118`, width ∝ `s`), helmet, shield, weapon; legs swing with `sin(walkPhase)`, head bobs 2% of head size.
  - `<Crowd path: Pt[] count: number spacing: number speed: number faction horizonY groundY minS?: number = 0.12 maxS?: number = 1 seed?: number />` — soldier `i` sits at `t = (start + i*spacing - frame*speed)` along the path (wraps), scale `depthScale(y)`, drawn back-to-front by `y`.

- [ ] **Step 1: Write the failing tests** in `path.test.ts` (`import {test} from 'node:test'; import assert from 'node:assert/strict'; import {pointAt, depthScale} from './path.ts'`)

```ts
test('midpoint of straight line', () => { const p = pointAt([[0,0],[100,0]], 0.5); assert.equal(p.x, 50); assert.equal(p.y, 0); });
test('arc length across uneven segments', () => { const p = pointAt([[0,0],[10,0],[10,30]], 0.5); assert.deepEqual([p.x, p.y], [10, 10]); });
test('zero-length segment', () => { const p = pointAt([[0,0],[0,0],[0,40]], 0.25); assert.ok(Number.isFinite(p.y)); assert.equal(p.y, 10); });
test('t clamped', () => { assert.deepEqual(pointAt([[0,0],[10,0]], 2).x, 10); });
test('clamp above horizon and below ground', () => {
  assert.equal(depthScale(100, 300, 1400, 0.12, 1), 0.12);
  assert.equal(depthScale(1500, 300, 1400, 0.12, 1), 1);
});
```

- [ ] **Step 2: Run** `cd tools/anim && node --test src/longform/` → FAIL (module not found).
- [ ] **Step 3: Implement** `path.ts`, `factions.ts`, `Soldier.tsx`, `Crowd.tsx`.
- [ ] **Step 4: Run tests** → PASS; then `npx tsc --noEmit -p tools/anim` → no errors.
- [ ] **Step 5: Commit** — `git commit -am "feat: code-drawn marching crowd for long-form scenes"` (add new files first).

---

### Task 6: Hero kit format, validator, generated types, `<Hero>`

**Files:**
- Create: `tools/longform/kit.py`, `tools/longform/tests/test_kit.py`, `tools/anim/src/longform/Hero.tsx`, `tools/anim/src/longform/kits.generated.ts` (written by `kit.py`, committed)
- Kit folder format: `library/characters/<id>/kit.json` + PNGs

`kit.json`:
```json
{"id": "tran-hung-dao", "name": "Trần Hưng Đạo", "height": 620, "model_sheet": "model_sheet.png",
 "images": {"stand.calm": {"file": "stand_calm.png", "anchor": [212, 1180], "blink": "stand_calm_blink.png"},
            "point.determined": {"file": "point_determined.png", "anchor": [260, 1176]}}}
```
`height` = on-screen pixel height at scale 1 on the 1440p frame. Keys are `pose.expression`. `anchor` comes from `cutout.cut`.

**Interfaces:**
- Consumes: `cutout.cut`, `cutout.check` (Task 4), `paths.library()` (Task 3)
- Produces:
  - `kit.load_kit(kit_id: str) -> dict`
  - `kit.validate_kit(kit_dir: str) -> list[str]` — problems: missing `kit.json` keys (`id`, `name`, `height`, `images`), file missing, image not RGBA / no transparency (`cutout.check`), anchor outside the image, blink file missing or a different size from its pose.
  - `kit.add_image(kit_id: str, key: str, raw_src: str, blink_src: str | None = None) -> list[str]` — runs `cutout.cut` into the kit folder, records file + anchor (+ blink), returns `validate_kit` problems.
  - `kit.write_ts(out: str = "tools/anim/src/longform/kits.generated.ts") -> None` — writes `export const KITS = {...} as const;` and `export type HeroKey = 'tran-hung-dao/stand.calm' | ...` for every valid kit; refuses (exit 1) if any kit has problems.
  - `<Hero image: HeroKey x: number groundY: number s?: number enter?: 'left' | 'right' | 'none' at?: number keys?: {at: number; image: HeroKey}[] />` (`HeroKey` = `'<kit id>/<pose.expression>'`) — image path `staticFile('library/characters/<id>/<file>')`; anchor placed at `(x, groundY)`; scale `s * height / imageHeightAboveAnchor`; breathing `scaleY 1 ± 0.008` at 0.25 Hz from the anchor; blink swaps to the blink file for 4 frames every 95–125 frames (seeded) when it exists; `keys` cut to a new image with a 4-frame cross-fade; `enter` slides 600 px with `spring` over ~18 frames; soft ellipse shadow under the anchor (`rgba(40,30,20,0.25)`, width 40% of image width). Prop types use `HeroKey`, so an unknown `id/pose.expr` fails `tsc`. With no valid kits, `write_ts` emits `export type HeroKey = never`.
  - CLI: `python -m tools.longform.kit validate <id>`, `... add <id> <key> <raw.png> [--blink raw_blink.png]`, `... ts`

- [ ] **Step 1: Write the failing tests** (temp `LONGFORM_ROOT`, synthetic green-screen PNGs from Task 4's helper)

```python
def test_add_and_validate(self):
    probs = kit.add_image("hero-x", "stand.calm", raw, blink_src=raw_blink)
    self.assertEqual(probs, [])
    k = kit.load_kit("hero-x"); self.assertIn("anchor", k["images"]["stand.calm"])
def test_missing_image_file(self):
    os.remove(path_of("stand_calm.png"))
    self.assertTrue(any("missing" in p for p in kit.validate_kit(kdir)))
def test_blink_size_mismatch(self):
    ...  # blink 10 px narrower -> problem mentions "blink"
def test_write_ts_lists_keys(self):
    kit.write_ts(out); src = open(out).read()
    self.assertIn("'hero-x/stand.calm'", src)
```

- [ ] **Step 2: Run** `.venv/bin/python -m unittest tools.longform.tests.test_kit -v` → FAIL.
- [ ] **Step 3: Implement `kit.py` and `Hero.tsx`.**
- [ ] **Step 4: Run tests** → PASS.
- [ ] **Step 5: Type gate check** — create a throwaway `tools/anim/src/longform/_bad.tsx` using `<Hero image="hero-x/fly.happy" .../>`, run `npx tsc --noEmit -p tools/anim`, expect an error naming `fly.happy`; delete the file.
- [ ] **Step 6: Commit** — `git add tools/longform/kit.py tools/longform/tests/test_kit.py tools/anim/src/longform && git commit -m "feat: hero kit format, validator and Hero component"`

---

### Task 7: Image generation wrapper, style lock draft, spike assets

**Files:**
- Create: `tools/longform/imagegen.py`, `tools/longform/tests/test_imagegen.py`, `tools/longform/stage.py`, `library/style/longform_v1.json`, `projects/000-spike/` (via `create_project(0, "spike", "Spike", [])`), `projects/000-spike/images/prompts/{BG01,THD_sheet,THD_stand_calm,THD_stand_calm_blink,THD_point_determined}.txt`

**Interfaces:**
- Consumes: `paths`, `project.create_project`, `kit.add_image`, `kit.write_ts`
- Produces:
  - `imagegen.agy_task(prompt: str, refs: list[str], name: str, aspect: str) -> str` — same preamble/`ImagePaths` contract as `tools/gemini/agy_images.py` `PREAMBLE`.
  - `imagegen.generate(prompt: str, refs: list[str], out_dir: str, name: str, aspect: str = "16:9") -> list[str]` — runs `agy -p` (model `gemini-4-argon-high`, timeout 900 s, 3 attempts, quota stop words as in `agy_images.py`) and collects outputs like `find_outputs`. Returns saved file paths in `out_dir`. Uses Pillow for size checks (no `sips`).
  - `stage.stage(project_dir: str, files: list[str]) -> str` — copies the listed workspace-relative files (backgrounds, kit folders) into `<project>/public/` keeping their relative paths; returns the public dir. Never links or copies the whole workspace.

`library/style/longform_v1.json` (draft; the owner's spike verdict finalises it):
```json
{"id": "longform-v1", "aspect": "16:9", "approved": false,
 "background": "2D hand-drawn European comic illustration: clean dark ink outlines, flat muted watercolor fills, light aged-paper texture, warm earth palette, eye-level camera, detailed scenery. Empty of people and animals. No text, no letters, no signs with writing.",
 "character": "Same ink-and-watercolor comic style. Cartoon proportions about 4 heads tall, large round head, simple face: dot eyes, simple brows, small line mouth. Fully clothed in period-accurate clothing. Full body, feet visible, standing on nothing. Plain flat chroma green background #00B140 filling the whole frame, no floor, no shadow, no text.",
 "negative": "photorealistic, 3D render, anime, stick figure body, text, letters, watermark, extra people, cropped feet",
 "chroma": "#00B140", "notes": ""}
```

Spike prompts (structured spec per the prompt standard: shot, angle, layout top/middle/bottom, setting, props with size against the body, light, must_not):
- `BG01`: wide eye-level view of a 13th-century Đại Việt riverbank at the Bạch Đằng estuary; a pale dirt path enters bottom-left and curves to the horizon at right-centre (path at least as wide as three people side by side in the foreground); river and low limestone hills behind; reeds, a few wooden stakes stored by the path; must_not: people, boats with crews, text, modern objects.
- `THD_sheet`: model sheet of the hero (Trần dynasty general, simplified period armour and robe, front view, full body).
- `THD_stand_calm`, `THD_point_determined`: edits of the approved sheet (attach it as ref), same character, one pose each, front 3/4 view, full body, chroma background.
- `THD_stand_calm_blink`: edit of `THD_stand_calm` with only the eyes closed; must_not: any other change.

- [ ] **Step 1: Write the failing test** for the pure part

```python
def test_agy_task_lists_refs_and_name(self):
    t = imagegen.agy_task("PROMPT", ["/a.png", "/b.png"], "spike_bg01", "16:9")
    self.assertIn('"/a.png", "/b.png"', t); self.assertIn("spike_bg01", t); self.assertIn("16:9", t)
def test_stage_copies_only_listed(self):
    pub = stage.stage(pdir, ["library/characters/hero-x"])
    self.assertTrue(os.path.exists(os.path.join(pub, "library/characters/hero-x/kit.json")))
    self.assertFalse(os.path.exists(os.path.join(pub, "projects")))
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** `imagegen.py`, `stage.py`. **Step 4: Run** → PASS.
- [ ] **Step 5: Generate spike assets** (live, uses Flow/agy quota): `BG01` and `THD_sheet` via agy; show both to the owner; on approval generate the three pose images from the sheet; run `python -m tools.longform.kit add tran-hung-dao stand.calm <raw> --blink <raw_blink>` and `... point.determined <raw>`; then `python -m tools.longform.kit validate tran-hung-dao` → no problems; `python -m tools.longform.kit ts`. Copy BG01 to `library/backgrounds/bach-dang-path-01.png` with a sidecar `bach-dang-path-01.json` `{"horizonY": <px>, "groundY": 1440, "path": [[x,y],...]}` measured on the 2560x1440 version (path points traced by eye in Remotion Studio or an image viewer).
- [ ] **Step 6: Commit** — `git add tools/longform library projects/000-spike && git commit -m "feat: image wrapper, style lock draft and spike assets"`

---

### Task 8: Spike composition, render, owner verdict

**Files:**
- Create: `tools/anim/src/longform/Spike.tsx`, `tools/anim/src/longform/Title.tsx`, `tools/longform/render.py`
- Modify: `tools/anim/src/Root.tsx` (register `Spike`: 2560x1440, 30 fps, 300 frames), `library/style/longform_v1.json` (verdict)

**Interfaces:**
- Consumes: `Crowd`, `Soldier` (Task 5), `Hero`, `KITS` (Task 6), `stage.stage` (Task 7), background sidecar JSON
- Produces:
  - `<Title kicker: string title: string sub?: string at: number />` — kicker in small spaced caps, title in Be Vietnam Pro, underline that draws left→right over 20 frames, `sub` types in letter by letter; colours `#2b2118` on the image (matches `march.mp4`).
  - `render.render(project_dir: str, composition: str, out: str, files: list[str], frames: str | None = None) -> str` — stages files, runs `npx remotion render src/index.ts <composition> <out> --public-dir=<public>` in `tools/anim` (or `npx remotion still` when `frames` is one number); returns `out`.

Spike timeline (frames at 30 fps): 0–15 fade from black; 0–300 background slow push-in 1.00→1.06 with 40 px pan right; 0–300 `Crowd` of 30 `nguyen` soldiers along the BG01 path, `spacing 0.03`, `speed 0.0012`; 45 `Title kicker="1288" title="Sông Bạch Đằng" sub="Quân Nguyên tiến về cửa biển…"`; 90 `<Hero image="tran-hung-dao/stand.calm">` enters from right to x=2050 on the path's foreground ground line, `s=1`; 180 key → `point.determined`; a boolean prop `boil` (default `false`) wraps the crowd in an SVG `feTurbulence`+`feDisplacementMap` filter that changes seed every 3 frames, for the owner to compare line blending.

- [ ] **Step 1: Still check** — `.venv/bin/python -m tools.longform.render projects/000-spike Spike projects/000-spike/render/spike_f150.png --frames 150` → PNG exists, 2560x1440 (check with Pillow), hero feet on the path, no soldier drawn above the horizon.
- [ ] **Step 2: Render both variants** — `spike_1440p.mp4` (`boil=false`) and `spike_boil_1440p.mp4` (`boil=true`). Expected: two 10-second files in `projects/000-spike/render/`.
- [ ] **Step 3: Owner verdict** — send both paths (and Telegram note via `tools/notify.py`). Ask: does the hero blend with the background; boil on or off; hero proportions right; crowd size and colours right. Record answers in `library/style/longform_v1.json` `notes`, set `approved: true` only on the owner's yes. If the owner rejects, adjust prompts/components and re-render — at most 2 rounds — before starting Plan 2.
- [ ] **Step 4: Commit** — `git add tools/anim/src tools/longform library/style && git commit -m "feat: 10-second long-form spike and style lock verdict"`
