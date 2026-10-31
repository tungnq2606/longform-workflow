# Image prompts with a locked character style

Every character image uses the channel's style: the clothed stick figure (`style/stickman_v1.json`; Fossil Receipts `style/stickman_v2.json`).
Claude never writes character prompts by hand; it fills `cast.json` and `shots.json` and runs the generator,
which pastes the style block word for word and refuses to write prompts that break the rules.

## Flow for one video

1. Claude writes `VIDEO/images/cast.json` (characters, pose library, locations, optional era) and
   `VIDEO/images/shots.json` (one entry per scene, linked to the voice block and sentence).
2. `python3 tools/imageprompts/make_prompts.py VIDEO` writes `VIDEO/images/prompts/`: one `.txt` per image,
   `manifest.json` (order, references, where to save) and `prompts.md` (manual pack with Vietnamese notes).
   Images come in this order:
   - a model sheet for each character that appears in scenes, animals too (views, up to 8 poses, expressions);
   - **the cast and pose sheet: one image with every character and every pose the script uses** (owner rule).
     It is never generated: `agy_images.py` pastes the approved model sheets together (`compose_cast_sheet.py`)
     as soon as the last one is approved, so it cannot drift from them;
   - the scenes.
3. (Shorts era; `agy_images.py` and the rest of `tools/gemini/` are archived in
   `/Users/quoctung/Documents/AI/archive/2026-10-31/workspace-code/tools/gemini/`) `agy_images.py VIDEO` generated the images with Gemini through the Antigravity CLI.
   It finds the files itself, keeps every variant in `images/raw/`, checks size and ratio, and turns scenes into
   2560x1440 frames in `images/frames/`. Sheets stop for approval: `--approve ID [--variant N]` copies the chosen
   sheet to `images/refs/`. Everything after a sheet waits until that sheet is approved.
4. Manual route (Gemini app or Flow, e.g. for 2K output): follow `prompts.md`, then
   `agy_images.py VIDEO --import ID FILE`.

`make_prompts.py VIDEO --check` re-validates, including prompt files edited by hand.
`style_test.py TEST_DIR` compares candidate styles before one is locked: same model sheets, one prompt per style (example: `channels/horror-tales/style-test/`).
A style may set `side_view`, `back_view` and `expression_unit` to replace the stick-figure wording on model sheets.
Tests: `python3 -m unittest discover -s tools/imageprompts/tests`.

## Who makes which image

Every manifest item has a `route`:
- `compose`: the cast sheet, pasted from the approved model sheets; `--import` refuses it, the runner never generates it.
- `manual`: the model sheets, the first scene and any shot with `"key": true` in shots.json
  (opening, climax). The owner makes these in Google Flow with Nano Banana Pro and drops them into the
  dashboard (`--import`). The runner skips them unless `--include-manual` or `--only ID` is given.
- `agy`: all other scenes, generated automatically through the Antigravity CLI (1376x768, upscaled to 1440p).
Thumbnails: `agy_thumb.py` for quick ideas; the final one is made by hand in Google Flow (Nano Banana Pro) and uploaded (resized to 1280x720).
Shots can opt out of the first-scene default with `"key": false`.

## Rules the validator enforces

- The STYLE block is in every prompt, unchanged. To change the style, add `stickman_v2.json`; never edit v1.
- Every character, pose, expression and location used in `shots.json` exists in `cast.json` / the style file.
- Every character a scene shows has `"model_sheet": true`, and every pose it uses is in its `sheet_poses` (max 8),
  so the composed cast sheet always holds every used pose.
- At most 3 reference images per image (Antigravity `generate_image` limit) and 4 named characters per scene.
- No third-party brand words (the reference sheet in `style/reference/` is third-party: study only, never attach).
- Scene prompts carry the 16:9 format line, the no-text line and the "do not copy the sheet" line.

## What the live tests showed (2026-10-22)

- `agy` makes 16:9 JPEGs of 1376x768 (no size option). Frames are upscaled with `sips` to 2560x1440; use the
  Gemini app (2K download) for frames that need to be sharper.
- The image subagent may try up to three times when it judges a result wrong, so one item can cost up to three
  images. All tries are kept as variants.
- Dense sheets with a label under every figure got mislabelled (and once drew headless figures). The cast sheet
  therefore prints each name once above its group and labels only the expression heads.
- Google Flow (2026-10-25) ignored the attached model sheets for the cast sheet when the prompt named them
  "Image 1 / Image 2" and also carried the full text cards. The cast sheet prompt now names each sheet by the
  title printed on it, says the sheet wins over any differing text, and drops the text card for characters that
  have a model sheet. Keep the cards in cast.json matching the approved sheets: scenes still use the cards.
- That still failed (video 003: Flow redrew HUNTER and MAKER off-model, likely because the STYLE text describes
  bare stick limbs and 3.7-head proportions that the sheets do not have). So when every character on the cast
  sheet has a model sheet (animals too) holding all of its used poses, the cast sheet is composed, and since the
  same day this is the only way: the validator refuses a cast without it, and the runner composes the sheet by
  itself after every model-sheet approval. An animal sheet prompt that said "three rows" but described two got
  the attached HUNTER sheet's expression heads as row 3; the row count is now exact and animal sheets say "no people".
- The agent's own report of the model it used was wrong ("Imagen 3" for a Nano Banana-sized image): the runner
  trusts files only.
