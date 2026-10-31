# YouTube upload and scheduling

Uploads a finished video to YouTube with the YouTube Data API v3, either as a
private video or scheduled to go public at a set time (`publishAt`).

Based on `common/youtube-upload` from https://github.com/junjunjunbong/youtube-skill
(MIT, commit 1b7fa1d, 2026-07-17; licence in `LICENSE-youtube-skill`).
`youtube_auth.py`, `manifest.py` and `youtube_upload.py` are copied unchanged;
`make_manifest.py` and `yt.sh` are ours.

## Safety

- Nothing is uploaded unless `yt.sh upload` is run. `yt.sh check` is a dry run.
- Uploads are always private; with a time set they become public at that time.
- Built in for every video: not made for kids, altered/synthetic content = yes
  (AI voice), category Education, subscribers not notified on upload.
- `make_manifest.py` refuses videos whose VIDEO.md says `Status: published`.
- The OAuth token (scope `youtube.force-ssl`) lives outside the workspace, one per channel.
  The tool talks only to Google APIs.

## One-time setup (owner)

1. Google Cloud console: create a project, enable "YouTube Data API v3".
2. OAuth consent screen: External, add your Google account as a test user.
3. Credentials: create an OAuth client ID of type "Desktop app", download the JSON
   and save it as `~/.config/youtube-upload/client_secret.json`.
4. `tools/youtube/yt.sh setup` (creates `.venv`, installs the Google client).
5. Per channel: `tools/youtube/yt.sh auth fossil-receipts` and pick that channel
   (brand account) in the Google screen. Repeat for `median-worker`.

Known API limits:
- Until the API project passes YouTube's audit, videos uploaded through it are
  locked as private: a scheduled video will not go public, and the lock cannot be
  lifted in Studio or appealed; the video must be re-uploaded through Studio
  (https://support.google.com/youtube/answer/7300965). Until the project passes the
  YouTube API Services audit, upload and schedule in Studio by hand.
- One upload costs about 1,600 of the default 10,000 daily quota units;
  setting the thumbnail costs 50 more.
- A custom thumbnail needs a verified channel (phone verification in Studio)
  and must be JPEG or PNG under 2 MB.
- Not handled here: subtitles, pinned comment, comment settings, end screens.
  Do those in Studio after the upload.

## Per video

```
python3 tools/youtube/make_manifest.py VIDEO --at "2026-10-30 09:00"   # time in America/New_York; --tz to change
tools/youtube/yt.sh check VIDEO     # dry run: prints what would be sent
tools/youtube/yt.sh upload VIDEO    # real upload; result JSON lands in VIDEO/upload/
```

`make_manifest.py` reads `upload/upload.txt` (TITLE, DESCRIPTION between the
dashed lines, TAGS), `render/*_1440p.mp4` and `upload/thumbnail.png` (or .jpg),
and writes `upload/manifest.json`. Leave out `--at` for a private upload with no schedule.
