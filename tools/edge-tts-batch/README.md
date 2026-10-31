# TTS Batch Runner (Edge, local)

Pick `.txt` files, press Run. For each file the extension pastes the text into ElevenLabs Text to Speech, clicks Generate, clicks Download, and saves `<file name>.mp3` into `Downloads/tts/`.

## Install
1. `edge://extensions` -> Developer mode -> Load unpacked -> this folder.
2. `edge://settings/downloads` -> turn off "Ask me what to do with each download".

## Use
1. Open elevenlabs.io Text to Speech and choose your voice and model. Leave them alone during the run.
2. Click the extension icon (a small popup opens under it). Click "Chọn file .txt" and select `01.txt` to `10.txt`.
3. Click Run, then click again to confirm. Progress shows in the popup and in a small box on the ElevenLabs page.

Notes
- Test with `02.txt` first. Each Generate spends credits. The run stops at the first failure and never retries.
- If the popup closes when the file dialog opens, use "Mở cửa sổ riêng" first, or drag the files onto the popup.
- Files must be named like the audio you want (`01.txt` becomes `01.mp3`). The browser can only save inside Downloads, so move `Downloads/tts/` afterwards.
- Selectors (checked on a saved page, 2026-10-21): `data-testid` `tts-editor`, `tts-generate`, `tts-download-latest-button`. A redesign of the page can break them. The behaviour of the Download button after a real generation has not been observed.
- Check ElevenLabs terms before automating the web interface.
