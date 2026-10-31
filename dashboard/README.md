# Studio dashboard

One local page for the whole workflow of both channels: `dashboard/start.sh` (or `python3 dashboard/server.py`),
then http://127.0.0.1:8765. It listens on 127.0.0.1 only and uses Python's standard library.

Screens: video board, topic scout, script and sources, characters and style, shots and images, voice,
preview and render, upload texts. The bottom bar has the Claude box (requests in Vietnamese; Claude Code runs
headless in the open video's folder, one resumable session per video, history in `VIDEO/.dashboard/`) and the
job list with live logs.

What the buttons run:
- Tạo prompt / Kiểm prompt: `tools/imageprompts/make_prompts.py VIDEO [--check]`
- Tạo ảnh (Gemini), Tạo lại, Duyệt, Tải ảnh lên: `tools/gemini/agy_images.py` (`--only`, `--redo`, `--approve`, `--import`)
- Tạo text giọng đọc: `tools/pipeline/voice_text.py`; mp3 files dropped on the voice page go to `audio/NN.mp3`
- Dựng video: `tools/anim/render_frames.sh` when the video has generated images, else `tools/anim/render.sh`
- Chạy đo (topics): `tools/research/scout.py` on the phrases, results in `channels/<id>/research/scout/`

Channels come from `channels/*/channel.json`; `config.json` only lists `extra_channels` (the "demo" channel shows `tools/imageprompts/examples`).
Claude's allowed tools for dashboard requests are also there. Jobs live in memory; logs stay in `dashboard/jobs/`.

## Who does what (to save the Claude Team quota)

| Work | Done by |
|---|---|
| Measuring search phrases (views, freshness, small channels) | `scout.py` + yt-dlp, no AI |
| Suggesting phrases, topic research, gathering sources | Gemini via `agy` ("Gửi Gemini", "Gemini gợi ý cụm từ"); answers saved in `channels/<id>/research/gemini/` (or the video's research/gemini/) |
| Generating every image (sheets, scenes) | Gemini via `agy_images.py` |
| Reviewing every image against the cast sheet ("Gemini kiểm ảnh") | Gemini via `tools/gemini/agy_review.py` -> `images/runs/review.json` |
| Thumbnails ("Gemini tạo thumbnail"; the title words are drawn by code, image models misspell) | Gemini via `tools/gemini/agy_thumb.py` |
| Viewer simulation, title/thumbnail/tag drafts, competitor analysis | Gemini presets on the script, upload and topics pages |
| Script writing and fact acceptance, cast/shot lists and image prompts, overlays, fixes, render setup | Claude ("Gửi Claude") |
| Validation, timing, upscaling, render, subtitles, chapters | code, no AI |

Gemini jobs run `agy -p` in `dashboard/agy_work/` with `--dangerously-skip-permissions` (headless agy cannot ask; its terminal sandbox stays on).
Per the delegation blog the owner follows, factual text written by Gemini is a draft: Claude checks it against the sources before it goes into a script.

All Gemini calls use Gemini 4 Argon high (owner: the Ultra plan quota is high).

## 3D office (`/office`)

http://127.0.0.1:8765/office is a decorative, read-only 3D view of the same jobs (three.js 0.170.0 bundled in `vendor/three/`, MIT licence; page in `office/index.html`,
font Be Vietnam Pro in `office/fonts/`). It only reads `/api/state` and `/api/job`; the normal dashboard does not depend on it. Version 1 (stick-figure staff) works;
version 2 is specified in `HANDOFF.md` section 12 and not built yet.
