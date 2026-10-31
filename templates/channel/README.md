# New channel

1. Copy this folder: `cp -R templates/channel channels/<id>` (id = short kebab-case name, e.g. `fossil-receipts`).
2. Fill `channel.json`: id (same as the folder), name, handle, about, language, style. Set `"status": "archived"` to hide a channel from the dashboard without deleting it.
3. Image style: `style` names a file in `tools/imageprompts/style/` (`stickman-v1` -> `stickman_v1.json`).
   For a different look, add a new style file with the same keys (copy `stickman_v1.json`, then change the STYLE block, forbidden words and limits) and run the tests in `tools/imageprompts/tests`. Never edit a style that published videos used; add a new id instead.
4. Write `CHANNEL_SETUP.md` (copy the structure of `channels/fossil-receipts/CHANNEL_SETUP.md`: positioning, name check, description, keywords, upload defaults, settings, brand, content rules, playlists, licences).
5. Brand: `brand/` holds the avatar (800x800), banner (2560x1440, safe area 1546x423) and watermark (150x150). Character art comes from make_prompts (brand/images/cast.json + shots.json), text is drawn by code (see `channels/fossil-receipts/brand/brand.py`).
6. The dashboard shows the channel on its next page load. New videos: dashboard "Video mới", or `tools/pipeline/new_video.sh <id> 001 short-slug`.
