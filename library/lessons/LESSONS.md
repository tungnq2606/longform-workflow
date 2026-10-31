# Công Trường Lịch Sử: lessons per video

Read this before planning the next Short. Prompt-level rules that Gemini's reviews keep finding are also merged
automatically into `prompt_lessons.json` (max 40, added to every prompt as a MUST block); this file keeps the
process lessons, the numbers and the reasons behind them.

## Veo credits per video

`python3 tools/shorts/credit_report.py channels/vn-history` (run after each video and paste here). Prices are rough (veo-lite ~12, veo-fast ~20) until a video is made with the balance logging added on 2026-10-30; from then on the Credits column is measured.

| Video | Shots (active) | veo-lite | veo-fast | lost by gflow (maybe billed) | Clips per shot | Credits | Credits per shot | vs previous |
|---|---|---|---|---|---|---|---|---|
| 002-bach-dang | 20 (6) | 33 | 14 | 4 | 2.35 | ~676 (max ~732) | 33.8 |  |
| 003-dia-dao-cu-chi | 21 (4) | 36 | 6 | 4 | 2.00 | ~552 (max ~600) | 26.3 | -22% |

Check on 2026-10-30: the Flow balance fell 995 credits (11,746 to 10,751) between 2026-10-29 13:17 and the end of 003, while the clips logged in that window (38 veo-lite, 6 veo-fast, 4 lost by gflow) come to ~624 at the rough prices. Either the real prices are higher or the account spent credits outside gflow (manual Flow use); the per-clip log will tell.

## Next video: Trống đồng Đông Sơn (design rules, written 2026-10-30 before planning)

From a risk review of the plan (ROADMAP_IDEAS.md item 4) checked against the 002 and 003 lessons. Enforced by
`make_shorts_prompts.py --check` where marked [lint].

Facts first (each needs a row in research/sources_log.csv before it is spoken or drawn):
- Which drum is shown (Ngọc Lũ has a 14-ray star; other drums differ). Name it in the script, draw only that one.
- Casting method: scholars still debate lost-wax vs piece moulds. Say only what the source says; "cast upside down" and
  bronze spacers ("con kê") need their own source rows.
- The Luy Lâu / Bắc Ninh mould find: site, year, who dug it.
- Birds and boats on the drum face run counter-clockwise: source row.

Checked 2026-10-30 (script v2, 004 research/sources_log.csv). Gemini's v1 had homepage-only sources and three errors:
- No official weight for Ngọc Lũ (86 kg is only on travel/wiki pages): not spoken. Official: face 79.3 cm, height 63 cm,
  14-ray star, bands move counter-clockwise (BTLSQG, Cục Di sản).
- Pouring: the old view is mould upside down, sprue at the foot; the Luy Lâu mould study (Trương Đắc Chiến 2022) puts the
  sprue in the centre of the star. The script says "có thể"; the pouring shot shows bronze going into a cup on top of the
  mould centre, not into the foot.
- Luy Lâu: ~1,000 fragments in 2014-2015 (3rd-4th c., Bắc thuộc) plus 2,300+ announced 2024, so "hàng nghìn"; "cho thấy",
  never "chứng minh".
- Drawable facts from the moulds: outer shell clay + rice husk, made on a turning table; outer mould = 1 face piece + 2 body
  pieces, one solid core; patterns carved or stamped into the inside of the outer mould; spacers of fired clay.

One drum everywhere:
- One key image of the drum (key: true, route manual, Nano Banana Pro). Every later shot with the drum is edit_of that
  image or attaches it with extra_refs. A fresh prompt per shot gives a different drum each time.
- Medium and wide shots describe only the shape: flat face, bulging upper body, straight waist, flared foot, paired
  handles, plain concentric rings. No figures on the face in those shots.

Drum face close-up:
- Still image, no motion [lint: close-up + pattern words + motion is refused]. Veo makes dense lines shimmer and morph.
- A reference drawn by us (star + concentric bands + bird ring as plain vector shapes, tools/kit) can go in extra_refs.
  Never a museum photo (third-party image rule).
- must_not: letters, numbers, Chinese/Aztec/Indian motifs, a spinning face.

Mould cross-section:
- Two shots joined by a dissolve: A empty mould with core and outer shell; B = edit_of A, only the gap filled with glowing
  bronze. Both stills [lint: liquid in a cutaway + motion is refused]. Veo pours liquid through walls in cutaways (S08B).
- Sizes against the body or a prop, never "3 mm" [lint]. Draw the gap clearly visible, e.g. "as wide as a finger".
- Spacers only if the voice names them.

Pouring:
- Exterior view, not a cutaway. Start frame: crucible already tilted, the bronze stream already touching the pouring cup.
- Motion: only the stream keeps flowing, slowly; the people hold still. The auto clip rules add "liquid stays in its
  stream path" and "no flying sparks, no bursts, thin flat smoke" to every shot with liquid or fire.
- Mid-tone light: the glow must not burn the frame white or leave the rest black.

Breaking the mould:
- Two shots, hard cut. Shot 1: wooden mallet already touching the clay shell, a small crack already drawn; motion = one
  short tap, the crack grows a little. Shot 2: the finished drum standing among broken shell pieces; still or light only.
- Never ask Veo to break the whole mould or reveal the drum in one clip.

Furnace and bellows: exact number of workers, each hand described; must_not sparks fountains, thick smoke, extra fires.

Budget: at most 4 active shots [lint]; everything else ambient or still. 003 cost ~552 credits with 4 active shots.

## 003 Địa đạo Củ Chi (published 2026-10-30)

### Numbers
- 21 shots, 10 voice blocks, ~92 s at Vbee speed 1.13.
- Images: 51 generations for 21 shots (2.4 per shot); first-try pass 10/21 (48%).
  Worst: S02A 10 tries, S07C 6, S05B 5.
- Clips: 36 veo-lite + 6 veo-fast calls (~550 credits). First-try veo-lite pass 14/21 (67%; 002 was ~55%).
  Worst: S10A 6 lite tries then still image, S08B 4 lite + 2 fast, S04A 3, S09B 3.
- gflow: 6 lite submits ended in exit 9 (Flow may have billed), 3 downloads missed (exit 7, fetched again free),
  12 failed 1080p exports; S05A, S05B, S06A, S06C kept the 720p clip after 3 export failures.
- Speed after the fixes below: ~2 min per veo-lite clip, was ~6 min.

### Prompts
1. Never put scene-type rules in the shared style block. A cutaway sentence in STYLE_LOCK turned the surface shot
   S02A into a half cutaway 6 times in a row. Cutaway text goes only on cutaway shots; surface shots say
   "Exterior above-ground view only".
2. Write every shot as a structured spec (shot, angle, top/middle/bottom, setting, people with
   who/where/pose/hands/gaze/wear, props with what/size/where/state, light, must_not) and every clip as motion
   (camera, mover, action, speed, end, still). `make_shorts_prompts.py --check` rejects missing fields and vague
   words ("a few", "some", "dramatic"). Use numbers and sizes against the body ("as wide as the shaft").
3. A travelling object moves in the direction its front faces in the start frame. S06C failed because the spec said
   "left to right" while the helicopter in the image faced left.
4. The clip prompt names only what is visible and what moves. S09B's prompt named the medical station that sits
   underground; Veo drew a whole medical tent on the empty surface twice.
5. Image review passes 4/5 with small faults left in (S08B kept two trapdoors although must_not forbade it). Look
   at a 4/5 key image before its clip starts if the fault touches what the clip animates.

### Veo and cutaways
6. Wide cutaways with many empty chambers are not animated. S10A (4 empty chambers + visitors on the surface)
   failed 6 times: soil falling down shafts, extra visitors inside empty rooms, wind streaks, then shipped as a still
   image. Plan such shots as stills from the start (no motion block, so flow_clips.py skips them); that saves ~72 credits.
7. Liquid above an opening gets poured through it. S08B (water dip over a shut trapdoor) passed once at veo-lite
   after a Gemini rewrite; veo-fast then poured the water through both hatches twice. Animate only something
   small and local (lamp flame, a hand) in such frames, or keep the passing veo-lite clip.
8. veo-fast must start from the prompt that passed at veo-lite. Before the fix (2026-10-30, `flow_clips.py`
   `override()`), veo-fast went back to the base prompt that had already failed 3 times at lite.
9. Ambient cutaways (digging, hoisting, crawling) still drop soil "by themselves" despite the VEO_TAIL rule. Keep the
   mover's stroke short and the rest of the frame described as solid (S03A, S03B, S04A needed 2-3 tries).
10. Animals lose the 2D line style when they move fast (S08A dog). Use small head motions only.

### Pipeline and owner workflow
11. Gemini reviews run on side threads while Flow makes the next clip; lessons merge in the background; gap between
    Flow calls 30-75 s. Nothing may block a pause.
12. While automation runs, the dashboard locks "Tạo lại prompt", "Kiểm prompt" and "Chỉ tạo N ảnh"; a queued redo
    shows "⏳ Chờ làm lại" at once.
13. 1080p export timeouts (~47 s) are common and cost nothing. They are retried 3 times, then the 720p clip is kept.
14. A clip that ends in exit 9 after submit is never re-submitted automatically: check the Flow project first.
15. When a veo-fast clip fails twice after a 5/5 veo-lite, keep the lite clip and upscale it rather than spend
    the remaining fast retries.

### Script
16. Check every spoken figure against an official source. "120 km of tunnels" appears only on travel sites; UNESCO
    lists ~4 km best preserved, so it was not spoken.
17. Say what visitors see today is widened ("đoạn hầm ấy đã được mở rộng thêm"); the original tunnels were too small
    to crawl upright.

## 002 Bạch Đằng (finished)

From `003-dia-dao-cu-chi/images/build_shots.py`, applied to 003:
- One clear physical relationship per frame; exact head count ("exactly N people, nobody else").
- A tool that moves must already touch its target in the start image (S04A: 9 image tries, 6 clip tries, ended as
  a still).
- One moving subject per clip; everything else is told to stay still.
- Veo misreads cutaways (water fell through "air" under a hull): every clip states the earth block is solid.
- Veo adds boats, flags and birds mid-clip: no new people, vehicles, aircraft or animals enter.
- Smoke and water stay flat 2D and slow; no opaque clouds or bursts.
- Style references lent their river and stakes to new scenes: copy linework and palette only.
- Shots longer than ~5 s are split, so each clip uses only its first few seconds.
- Audio: clip sound at 0.18 under music and the main voice; Vbee speed 1.13 (3.88 syllables/s).
- Keep two renders: TikTok 1080p and YouTube 4K with the same audio.
