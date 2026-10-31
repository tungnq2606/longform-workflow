#!/usr/bin/env python3
"""Build 9:16 image & Veo prompts for a Shorts video (e.g. Công Trường Lịch Sử).

Usage:
  make_shorts_prompts.py VIDEO_DIR           write images/prompts/ (manifest.json, prompts.md, NNN_ID.txt)
  make_shorts_prompts.py VIDEO_DIR --check   validate shots.json and prompt files; exit 1 on errors
"""
import json
import re
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(os.path.dirname(HERE))
STYLE_DIR = os.path.join(WS, "tools", "imageprompts", "style")

VEO_STYLE = "Keep the exact flat 2D hand-drawn ink illustration style throughout, never photorealistic. No text, no UI."
VEO_TAIL = VEO_STYLE + " Sound: water and wind only; no voices, no talking, no speech, no music."


def load_style(style_id):
    p = os.path.join(STYLE_DIR, style_id.replace("-", "_") + ".json")
    if not os.path.exists(p):
        sys.exit(f"unknown style: {style_id} (expected {p})")
    return json.load(open(p, encoding="utf-8"))


def resolve_ref(vdir, ref):
    """Turn a workspace-relative or images-relative ref into a path relative to VIDEO_DIR/images/."""
    img_dir = os.path.join(vdir, "images")
    cand_img = os.path.join(img_dir, ref)
    if os.path.exists(cand_img):
        return ref
    cand_ws = os.path.join(WS, ref)
    if os.path.exists(cand_ws):
        return os.path.relpath(cand_ws, img_dir)
    return ref


def channel_swatch(vdir):
    """Workspace-relative path of the channel's approved style swatch (channel.json "style_swatch"), or None."""
    d = os.path.abspath(vdir)
    while d != WS and d != os.path.dirname(d):
        cj = os.path.join(d, "channel.json")
        if os.path.exists(cj):
            return json.load(open(cj, encoding="utf-8")).get("style_swatch")
        d = os.path.dirname(d)
    return None


# ---------------------------------------------------------------- prompt standard (owner, 2026-10-29)
# Generic descriptions made the models guess, and every guess cost a retry. A shot may describe its image as a
# structured "spec" and its clip as a structured "motion"; the builder writes the prompt text from them and --check
# refuses a spec that leaves something to guess (who is where, what each hand does, where each person looks, prop
# sizes, light, what must not appear; for clips: the one thing that moves, how fast, how it ends, what stays still).
VAGUE = ["some ", "several", "a few", "various", "many ", "etc", "beautiful", "epic", "stunning", "dramatic",
         "detailed", "nice", "cinematic", "dynamic", "suddenly", "quickly", "fast "]
PERSON_KEYS = ("who", "where", "pose", "hands", "gaze", "wear")
SPEC_KEYS = ("shot", "angle", "top", "middle", "bottom", "light", "must_not")
MOTION_KEYS = ("camera", "mover", "action", "speed", "end", "still")


def spec_text(sp):
    people = sp.get("people", [])
    out = ["SHOT: %s, %s." % (sp["shot"], sp["angle"]),
           "LAYOUT, top to bottom of the 9:16 frame: TOP: %s. MIDDLE: %s. BOTTOM: %s." % (sp["top"], sp["middle"], sp["bottom"])]
    if sp.get("setting"):
        out.append("SETTING: %s." % sp["setting"].rstrip("."))
    if people:
        out.append("PEOPLE: exactly %d, nobody else in the frame." % len(people))
        for n, pp in enumerate(people, 1):
            out.append("%d) %s, %s: %s; hands: %s; looking %s; wearing %s." % (
                n, pp["who"], pp["where"], pp["pose"], pp["hands"], pp["gaze"], pp["wear"]))
    else:
        out.append("PEOPLE: none, no person anywhere in the frame.")
    for pr in sp.get("props", []):
        out.append("PROP: %s (%s), %s%s." % (pr["what"], pr["size"], pr["where"], "; " + pr["state"] if pr.get("state") else ""))
    out.append("LIGHT: %s." % sp["light"].rstrip("."))
    out.append("MUST NOT: %s." % "; ".join(sp["must_not"]))
    return "\n".join(out)


def motion_text(m):
    still = m["still"] if isinstance(m["still"], list) else [m["still"]]
    return ("Camera: %s. What moves (nothing else): %s. Motion: %s, %s. By the end of the clip: %s. Everything else stays exactly as in the "
            "start frame: %s." % (m["camera"], m["mover"], m["action"].rstrip("."), m["speed"], m["end"].rstrip("."),
                                  "; ".join(still)))


# Shot shapes Veo kept breaking (vn-history 003, 2026-10-30): such shots stay still images unless the shot says
# why motion is safe ("allow_motion": "<reason>").
CUTAWAY_WORDS = ("cutaway", "cross-section", "cross section")
LIQUID_WORDS = ("water", "molten", "liquid", "melt", "pour", "flood", "well shaft")  # S08B, S09B: poured through hatches
PATTERN_WORDS = ("pattern", "engrav", "relief", "motif", "ornament", "inscription", "decorat")  # dense lines shimmer
UNIT_SIZE = re.compile(r"\b\d+(\.\d+)?\s?(mm|cm|millimet\w*|centimet\w*|inch(es)?)\b")
LIQUID_RULE = ("Every liquid stays inside its own container, channel or stream path: it never passes through walls, lids, "
               "earth or people, never splashes, sprays or drips, and its outline stays smooth.")
FIRE_RULE = ("Fire, embers and glowing metal keep their start size and colour: no flying sparks, no bursts, no new "
             "flames; any smoke is a thin flat 2D wisp that drifts slowly.")
FIRE_WORDS = ("fire", "flame", "furnace", "kiln", "forge", "ember", "molten", "glowing metal", "torch")


def has_any(text, words):
    return any(w in text for w in words)


def lint_video(data):
    """Video-level limits: every active shot costs veo-fast credits on top of veo-lite."""
    shots = data.get("shots", [])
    active = [s.get("id") for s in shots if s.get("motion_mode") == "active"]
    limit = data.get("max_active", 4)  # 002 had 6 active shots -> 14 veo-fast clips; 003 had 4 -> 6
    return ["%d active shots (%s), limit %d: make the rest ambient or still, or set \"max_active\"" % (
        len(active), ", ".join(active), limit)] if len(active) > limit else []


def lint(shot):
    """Problems that make a model guess; [] when the shot is fully specified."""
    errs, sid = [], shot.get("id")
    # what the image shows: the "must not" and "still" lists name things to avoid, so they do not count
    shown = [{k: v for k, v in (shot.get(f) or {}).items() if k not in ("must_not", "still")} for f in ("spec", "edit")]
    look = json.dumps(shown, ensure_ascii=False).lower()
    if UNIT_SIZE.search(look):
        errs.append("%s: size in units (%s); give sizes against the body or a prop ('as wide as a finger')"
                    % (sid, UNIT_SIZE.search(look).group(0)))
    if shot.get("motion") and not shot.get("allow_motion"):
        shape = look + json.dumps({k: v for k, v in shot["motion"].items() if k != "still"}, ensure_ascii=False).lower()
        if has_any(shape, CUTAWAY_WORDS) and has_any(shape, LIQUID_WORDS):
            errs.append("%s: liquid in a cutaway with motion (Veo pours it through lids and earth, S08B/S09B): "
                        "drop the motion (still image) or set allow_motion with the reason" % sid)
        if has_any(look, PATTERN_WORDS) and "close" in json.dumps((shot.get("spec") or {}).get("shot", "")).lower():
            errs.append("%s: close-up of a patterned surface with motion (fine lines shimmer and morph): "
                        "drop the motion (still image) or set allow_motion with the reason" % sid)
    sp = shot.get("spec")
    if sp:
        errs += ["%s spec: missing %s" % (sid, k) for k in SPEC_KEYS if not sp.get(k)]
        for n, pp in enumerate(sp.get("people", []), 1):
            errs += ["%s person %d: missing %s" % (sid, n, k) for k in PERSON_KEYS if not pp.get(k)]
        for n, pr in enumerate(sp.get("props", []), 1):
            errs += ["%s prop %d: missing %s" % (sid, n, k) for k in ("what", "size", "where") if not pr.get(k)]
        text = json.dumps(sp, ensure_ascii=False).lower()
        errs += ["%s spec: vague word %r" % (sid, w.strip()) for w in VAGUE if w in text]
    m = shot.get("motion")
    if m:
        errs += ["%s motion: missing %s" % (sid, k) for k in MOTION_KEYS if not m.get(k)]
        text = json.dumps(m, ensure_ascii=False).lower()
        errs += ["%s motion: vague word %r" % (sid, w.strip()) for w in VAGUE if w in text]
    return errs


def build_image_prompt(shot, st):
    if shot.get("spec") and not shot.get("edit_of"):
        shot = dict(shot, prompt="[STYLE LOCK]\n\n" + spec_text(shot["spec"]))
    if shot.get("edit_of") and shot.get("edit"):
        e = shot["edit"]
        shot = dict(shot, prompt="Edit the attached image. KEEP EXACTLY: %s. CHANGE ONLY: %s. MUST NOT: %s. Vertical 9:16, no text, no UI."
                    % ("; ".join(e["keep"]), "; ".join(e["change"]), "; ".join(e.get("must_not", []))))
    raw = shot["prompt"].strip()
    if shot.get("edit_of"):
        return raw
    body = raw.replace("[STYLE LOCK]", st["style"]).strip()
    if "[STYLE LOCK]" not in raw and not shot.get("custom_style"):
        body = st["style"] + "\n\n" + body
    neg = shot.get("negative", st.get("negative", "")).strip()
    if neg:
        body += f"\n\nAvoid: {neg}."
    return body


def veo_motion(shot):
    """The motion part of the clip prompt: written from "motion" when the shot has one, else its "veo_prompt"."""
    return motion_text(shot["motion"]) if shot.get("motion") else (shot.get("veo_prompt") or "").strip()


def veo_rules(shot, tail=None):
    """What follows the motion in every clip prompt: shared clip rules + the shot's sound line."""
    if "no voices" in veo_motion(shot).lower():
        return ""  # older shot lists carry their own rules
    rules = tail or (VEO_STYLE if shot.get("sound") else VEO_TAIL)
    scene = json.dumps([shot.get("spec"), shot.get("edit"), shot.get("motion"), shot.get("prompt")], ensure_ascii=False).lower()
    for words, rule in ((LIQUID_WORDS, LIQUID_RULE), (FIRE_WORDS, FIRE_RULE)):
        if has_any(scene, words) and rule not in rules:
            rules = rules.rstrip(".") + ". " + rule
    if shot.get("sound"):
        rules = rules.rstrip(".") + ". Sound: " + shot["sound"].rstrip(".") + " only; no voices, no talking, no speech, no music."
    return rules


def build_veo_prompt(shot, tail=None):
    """Shot motion + the video's shared clip rules (shots.json "veo_tail") + the shot's "sound" line."""
    vp = veo_motion(shot)
    if not vp:
        return ""
    rules = veo_rules(shot, tail)
    return vp.rstrip(".") + ". " + rules if rules else vp


def main():
    check_only = "--check" in sys.argv[1:]
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        sys.exit("usage: make_shorts_prompts.py VIDEO_DIR [--check]")
    vdir = os.path.abspath(args[0])
    img_dir = os.path.join(vdir, "images")
    shots_path = os.path.join(img_dir, "shots.json")
    if not os.path.exists(shots_path):
        sys.exit(f"missing {shots_path}")

    data = json.load(open(shots_path, encoding="utf-8"))
    st = load_style(data.get("style", "vn-ligne-claire"))
    # a video can tune the channel's style block and negatives to its own setting (e.g. underground clay
    # instead of rivers) without touching the channel style file
    if data.get("style_lock"):
        st = dict(st, style=data["style_lock"])
    if data.get("negative"):
        st = dict(st, negative=data["negative"])
    veo_tail = data.get("veo_tail")
    shots = data.get("shots", [])
    if not shots:
        sys.exit("shots.json has 0 shots")

    errs = lint_video(data)
    seen = set()
    save_map = {}
    for seq, sh in enumerate(shots, 1):
        sid = sh.get("id", "").strip()
        if not sid or sid in seen:
            errs.append(f"invalid or duplicate shot id: {sid!r}")
        seen.add(sid)
        save_map[sid] = f"frames/{seq:03d}_{sid}.png"
        if not (sh.get("prompt") or sh.get("spec") or sh.get("edit")):
            errs.append(f"shot {sid}: empty image prompt")
        errs += lint(sh)
        if sh.get("edit_of") and sh["edit_of"] not in save_map:
            errs.append(f"shot {sid}: edit_of {sh['edit_of']!r} must refer to an earlier shot")

    if errs:
        for e in errs:
            print("ERROR:", e)
        sys.exit(1)

    if check_only:
        print(f"OK: {len(shots)} shots validated (0 errors)")
        return

    prompts_dir = os.path.join(img_dir, "prompts")
    os.makedirs(prompts_dir, exist_ok=True)
    items = []
    md_lines = [f"# Prompts: {data.get('title', os.path.basename(vdir))}", ""]

    for seq, sh in enumerate(shots, 1):
        sid = sh["id"]
        refs = []
        if sh.get("edit_of"):
            refs.append(save_map[sh["edit_of"]])
        elif sh.get("style_ref"):
            # an approved neutral swatch (tools/shorts/style_swatch.py) replaces the channel's old video frames,
            # which lent their landscape and buildings to new scenes; a shot can opt out with "keep_style_ref"
            swatch = channel_swatch(vdir)
            refs.append(resolve_ref(vdir, swatch if swatch and not sh.get("keep_style_ref") else sh["style_ref"]))
        for r in sh.get("extra_refs", []):
            refs.append(resolve_ref(vdir, r))

        pfile = f"prompts/{seq:03d}_{sid}.txt"
        ptext = build_image_prompt(sh, st)
        vtext = build_veo_prompt(sh, veo_tail)
        open(os.path.join(img_dir, pfile), "w", encoding="utf-8").write(ptext + "\n")

        route = sh.get("route") or ("manual" if sh.get("key") else "agy")
        item = {
            "seq": seq,
            "id": sid,
            "kind": "scene",
            "order": seq,
            "block": sh.get("block", 1),
            "duration": sh.get("duration", 4.5),
            "xfade": sh.get("xfade", 12),
            "motion_mode": sh.get("motion_mode", "ambient"),
            "camera": sh.get("camera", ""),
            "vo": sh.get("vo", ""),
            "edit_of": sh.get("edit_of"),
            "refs": refs,
            "prompt_file": pfile,
            "veo_prompt": vtext,
            "veo_motion": veo_motion(sh),  # the motion alone: what Gemini rewrites after a failed clip
            "veo_rules": veo_rules(sh, veo_tail),  # flow_clips adds these after a Gemini-rewritten motion too
            "save_as": save_map[sid],
            "clip_as": f"../clips/{sid}.mp4",
            "approve": False,
            "route": route,
        }
        items.append(item)
        md_lines += [
            f"## {seq:02d}. `{sid}` (Block {item['block']}, {item['duration']}s, {item['motion_mode']})",
            f"- Refs: `{', '.join(refs) or 'none'}`",
            "### Image Prompt (9:16)",
            "```",
            ptext,
            "```",
            "### Veo Video Prompt",
            "```",
            vtext,
            "```",
            "",
        ]

    manifest = {
        "video": os.path.basename(vdir),
        "title": data.get("title", os.path.basename(vdir)),
        "style": data.get("style", "vn-ligne-claire"),
        "aspect": data.get("aspect", "9:16"),
        "hook_reuse": data.get("hook_reuse"),
        "items": items,
    }
    json.dump(manifest, open(os.path.join(prompts_dir, "manifest.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    open(os.path.join(prompts_dir, "prompts.md"), "w", encoding="utf-8").write("\n".join(md_lines))
    print(f"Wrote {len(items)} 9:16 prompts + Veo prompts to {prompts_dir} (0 errors)")


if __name__ == "__main__":
    main()
