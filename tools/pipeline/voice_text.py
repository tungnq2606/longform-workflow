#!/usr/bin/env python3
"""script/script.txt -> script/voiceover_final.txt and script/voiceover_tts/NN.txt (text to paste into the TTS tool).

script.txt: one paragraph per voice block, blank line between blocks; [src: ...] tags are removed.
Pronunciation fixes for the TTS voice live in script/pronounce.json, e.g. {"HUD": "H-U-D"}.
"""
import hashlib, json, os, re
from _common import video_dir

V = video_dir()
raw = open(os.path.join(V, "script", "script.txt"), encoding="utf-8").read()
paras = [p.strip() for p in raw.split("\n\n") if p.strip()]
spoken = [re.sub(r"\s+", " ", re.sub(r"\[src:[^\]]*\]", "", p)).strip() for p in paras]
pron_path = os.path.join(V, "script", "pronounce.json")
pron = json.load(open(pron_path)) if os.path.exists(pron_path) else {}
body = "\n".join("[%02d]\n%s\n" % (i, s) for i, s in enumerate(spoken, 1))
h = hashlib.sha256(body.encode()).hexdigest()[:12]
open(os.path.join(V, "script", "voiceover_final.txt"), "w", encoding="utf-8").write(
    "# VOICE-OVER (generated from script.txt). One block [NN] = one audio file audio/NN.mp3. Hash: %s\n\n" % h + body)
out = os.path.join(V, "script", "voiceover_tts")
os.makedirs(out, exist_ok=True)
total = 0
for i, s in enumerate(spoken, 1):
    for k, v in pron.items():
        s = re.sub(r"\b%s\b" % re.escape(k), v, s)
    open(os.path.join(out, "%02d.txt" % i), "w", encoding="utf-8").write(s + "\n")
    total += len(s)
words = sum(len(s.split()) for s in spoken)
print("%d blocks, %d words (~%.1f min at 150 wpm), %d characters for TTS" % (len(spoken), words, words / 150, total))
