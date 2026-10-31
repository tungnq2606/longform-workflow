"""Scenes for this video. S[block] = list of (sentence_no, fraction, svg_body).

sentence_no counts sentences inside the voice block (1 = first). fraction 0..1 starts a beat
part-way through a sentence. Use helpers from scene_kit (F, prop, bubble, strip, runner, track,
pie, stamp, note, chalkboard, tightrope, signpost, ...); see channels/median-worker/videos/001-*/visuals/scenes.py for examples.
"""
from scene_kit import *  # noqa: F401,F403

BG = {1: "#E4EEF6", 2: "#F6EFE2"}                 # background tint per block
CHAPTERS = {2: "Part two title"}                   # chapter card before these blocks (silence)
DESC_CHAPTERS = {1: "Intro", 2: "Part two title"}  # names written into upload/description.txt

S = {}
S[1] = [
    (1, 0, ground() + F(760, 470, 1.5, "wave", "both", "center", "smile") + T(1180, 320, "replace me", 46, "start", INK, True)),
]
S[2] = [
    (1, 0, ground() + F(300, 520, 1.25, "point", "flat", "right", "smirk") + prop("house", 1200, 600, 1.4)),
]
