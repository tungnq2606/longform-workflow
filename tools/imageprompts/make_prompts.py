#!/usr/bin/env python3
"""Turn a video's cast and shot list into image prompts that always carry the locked character style.

Usage:
  make_prompts.py VIDEO_DIR           write VIDEO_DIR/images/prompts/ (manifest.json, prompts.md, one .txt per image)
  make_prompts.py VIDEO_DIR --check   validate only; also re-checks the prompt files on disk; exit 1 on errors

Inputs in VIDEO_DIR/images/ (formats in README.md):
  cast.json   title, style id, optional era, characters (name, kind, card, ...), pose library, locations
  shots.json  ordered shots: id, location, scene, camera, characters with pose / expression / facing

Every prompt that shows a character contains the STYLE block of the style file word for word; the
validator refuses to write prompts that break that rule or any other rule listed in check().
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NAME_RE = re.compile(r"^[A-Z][A-Z0-9]{1,15}$")
POSES_PER_ROW = 7
MAX_SHEET_POSES = 8  # action poses on one model sheet (row 2); more do not fit legibly
NUM_WORDS = {3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}


def load_style(style_id):
    path = os.path.join(HERE, "style", style_id.replace("-", "_") + ".json")
    if not os.path.exists(path):
        sys.exit("unknown style: %s (expected %s)" % (style_id, path))
    return json.load(open(path, encoding="utf-8"))


def expr_text(st, key):
    return st["expressions"][key]


# ---------------------------------------------------------------- planning
def plan(cast, shots, st):
    """Decide which images exist, in which order, with which references. Pure function of the inputs."""
    lim = st["limits"]
    chars = {c["name"]: c for c in cast["characters"]}
    order = [c["name"] for c in cast["characters"]]
    # what the script uses, in order of first appearance, with use counts
    uses, exprs = {}, {}
    for sh in shots:
        for c in sh.get("characters", []):
            k = (c["name"], c["pose"])
            uses.setdefault(k, 0)
            uses[k] += 1
            exprs.setdefault(c["name"], [])
            if c["expression"] not in exprs[c["name"]]:
                exprs[c["name"]].append(c["expression"])
    used_chars = [n for n in order if any(k[0] == n for k in uses)]
    pairs = list(uses)  # first-appearance order
    # The cast sheet is never generated: it is pasted together from the approved model sheets
    # (compose_cast_sheet.py), so it always holds every character and every used pose exactly as approved.
    # check_refs() makes sure each used character has a model sheet listing all of its used poses.
    sheets = [pairs]
    # expression heads: every character has the same white circle head, so each expression is drawn once
    heads = []
    for sh in shots:
        for c in sh.get("characters", []):
            if c["expression"] not in heads and len(heads) < lim["max_expression_heads_per_sheet"]:
                heads.append(c["expression"])
    items = []
    model_sheets = [n for n in order if chars[n].get("model_sheet")]
    for n in model_sheets:
        items.append({"id": "sheet_" + n.lower(), "kind": "model_sheet", "character": n,
                      "refs": [], "save_as": "refs/sheet_%s.png" % n.lower(), "approve": True, "route": "manual"})
    # route "compose": made by agy_images.py itself as soon as the last model sheet is approved, never in Flow
    # (Flow redrew HUNTER and MAKER off-model from the attached sheets, video 003, 2026-10-25)
    items.append({"id": "cast_sheet", "kind": "cast_sheet", "characters": used_chars, "poses": pairs, "heads": heads,
                  "refs": ["refs/sheet_%s.png" % n.lower() for n in used_chars], "compose": True,
                  "save_as": "refs/cast_sheet.png", "approve": True, "route": "compose"})
    prev = None
    for n, sh in enumerate(shots, 1):
        # Attach only the model sheets of the characters in this shot (2026-10-28: the full cast sheet made the
        # model paste extra characters into scenes, 23 review rejections in Fossil Receipts 001). No characters:
        # no character reference at all. More characters than reference slots: fall back to the cast sheet.
        names = [c["name"] for c in sh.get("characters", [])]
        own = ["refs/sheet_%s.png" % x.lower() for x in dict.fromkeys(names)]
        if not names:
            refs = []
        elif len(own) <= lim["max_refs_per_image"] - (1 if sh.get("continue_from_previous") else 0) \
                and all(chars[x].get("model_sheet") for x in names):
            refs = own
        else:
            refs = ["refs/cast_sheet.png"]
        notes = []
        if sh.get("continue_from_previous") and prev:
            if len(refs) < lim["max_refs_per_image"]:
                refs.append(prev)
            else:
                notes.append("previous-scene reference dropped (reference limit)")
        refs += [r for r in sh.get("extra_refs", []) if len(refs) < lim["max_refs_per_image"]]
        save = "frames/%03d_%s.png" % (n, sh["id"])
        items.append({"id": sh["id"], "kind": "scene", "order": n, "refs": refs, "save_as": save,
                      "approve": False, "notes": notes, "characters": [c["name"] for c in sh.get("characters", [])],
                      # key images (reference sheets, the first scene, shots marked "key": true) are made by hand in the
                      # Gemini app with Nano Banana Pro at 2K; the rest go to Gemini through agy automatically
                      "route": "manual" if sh.get("key", n == 1) else "agy"})
        prev = save
    return items, {"uses": uses, "exprs": exprs, "heads": heads, "sheets": sheets}


# ---------------------------------------------------------------- prompt text
def char_line(c, cast_chars):
    return '"%s": %s' % (c, cast_chars[c]["card"])


def model_sheet_prompt(item, cast, st):
    chars = {c["name"]: c for c in cast["characters"]}
    c = chars[item["character"]]
    animal = c.get("kind") == "animal"
    poses = [cast["poses"][p] for p in c.get("sheet_poses", [])]
    lines = ['Create one character model sheet image for the character "%s": a single 16:9 landscape image %s.'
             % (c["name"], st["sheet_background"]), "", st["style"]]
    if animal:
        lines.append(st["animals"])
    keys = list(st["expressions"]) if not animal else c.get("sheet_expressions", [])
    # the row count is spelled out: "three rows" on an animal sheet without heads made Flow fill row 3 with
    # the attached HUNTER sheet's human expression heads (video 003, 2026-10-25)
    n_rows = 1 + bool(poses) + bool(keys)
    lines += ["", 'CHARACTER "%s": %s' % (c["name"], c["card"]), "",
              "LAYOUT, exactly %s, every figure complete, same scale, evenly spaced, never overlapping:"
              % {1: "one row", 2: "two rows", 3: "three rows"}[n_rows]]
    if animal:
        lines.append("Row 1, four full-body views of %s: front view, left side view, right side view, three-quarter view." % c["name"])
    else:
        # side_view / back_view / expression_unit default to the stick-figure wording; other looks set their own
        lines.append("Row 1, %s full-body views of %s: %s. %s; %s."
                     % (NUM_WORDS[len(st["turnaround"])], c["name"], ", ".join(st["turnaround"]),
                        st.get("side_view", "In side views the face is a single dot eye near the facing edge and a short mouth stroke"),
                        st.get("back_view", "in the back view the head is a blank white circle")))
    if poses:
        lines.append("Row 2, %d full-body action poses of %s: %s." % (len(poses), c["name"], "; ".join(poses)))
    if keys:
        lines.append("Row 3, %d %s of %s: %s." % (
            len(keys), st.get("expression_unit", "head-only expression circles"), c["name"], "; ".join("%s (%s)" % (k, st["expressions"][k]) for k in keys)))
    lines.append('TEXT: a title in the top-left corner reading "%s" in bold condensed capitals, and a short label in %s centred under each figure. No other text.'
                 % (c["name"], st["label_style"]))
    if animal and not keys:
        lines.append("No people, human heads or expression circles anywhere on this sheet; any attached image is only a drawing-style guide.")
    return "\n".join(lines)


def cast_sheet_prompt(item, cast, st):
    """Not a generation prompt: the cast sheet is pasted together from the approved model sheets."""
    return "\n".join([
        "DO NOT GENERATE THIS IMAGE. The cast sheet for \"%s\" is assembled from the approved model sheets (%s)"
        % (cast["title"], ", ".join(item["refs"])),
        "automatically when the last of them is approved (tools/gemini/agy_images.py VIDEO_DIR --compose does it by hand),",
        "so every character stays exactly as approved. Never make it in Flow or Gemini.",
        "", "STYLE (for reference only):", st["style"]])


def scene_prompt(item, sh, cast, st, sheet_ids):
    chars = {c["name"]: c for c in cast["characters"]}
    roles = []
    for i, r in enumerate(item["refs"], 1):
        if r.startswith("refs/cast_sheet"):
            roles.append("Image %d is the approved cast and pose sheet%s for this video: use it only for each character's identity (head, face, outline weight, clothing, colours, accessories and proportions)."
                         % (i, "" if r == "refs/cast_sheet.png" else " (part %s)" % r[-5]))
        elif r.startswith("refs/sheet_"):
            who = next((c for c in chars if "refs/sheet_%s.png" % c.lower() == r), r)
            roles.append("Image %d is the approved model sheet of %s: use it only for %s's identity (head, face, outline weight, clothing, colours, accessories and proportions); %s appears once in this scene."
                         % (i, who, who, who))
        elif r.startswith("frames/"):
            roles.append("Image %d is the previous scene: keep its location, background, palette and lighting." % i)
        else:
            roles.append("Image %d: %s." % (i, sh.get("extra_ref_roles", {}).get(r, "extra reference")))
    lines = (["REFERENCES: " + " ".join(roles) + " " + st["reference_guard"], ""] if roles else []) + [st["style"]]
    if any(chars[c["name"]].get("kind") == "animal" for c in sh.get("characters", [])):
        lines.append(st["animals"])
    if sh.get("background_people"):
        lines.append(st["background_people"])
    lines += ["", "SCENE: " + sh["scene"]]
    if sh.get("characters"):
        lines.append("CHARACTERS:")
        for c in sh["characters"]:
            card = chars[c["name"]]["card"]
            lines.append('- %s, exactly as labelled "%s" on the cast sheet (%s): %s; expression: %s; facing %s.'
                         % (c["name"], c["name"], card, cast["poses"][c["pose"]], st["expressions"][c["expression"]],
                            c.get("facing", "the viewer")))
    if sh.get("background_people"):
        lines.append("BACKGROUND PEOPLE: " + sh["background_people"])
    elif not sh.get("characters"):  # the style block and cast sheet otherwise invite the model to add figures
        lines.append("PEOPLE: none. This image shows no people, figures or faces at all.")
    lines += ["SETTING: %s. %s" % (cast["locations"][sh["location"]], st["setting_style"])]
    if cast.get("era"):
        lines.append(st["history_line"].format(era=cast["era"]))
    if sh.get("leave_space"):  # room for numbers and charts that Remotion draws on top
        lines.append("COMPOSITION: keep the %s of the frame calm and uncluttered (plain wall, sky or ground) for graphics that are added later." % sh["leave_space"])
    lines += ["CAMERA: %s." % sh.get("camera", "medium wide shot at eye level"), st["format_scene"], st["exclusion_scene"]]
    return "\n".join(lines)


# ---------------------------------------------------------------- validation
def check_refs(cast, shots, st):
    """Names, keys and limits in the inputs; must pass before any prompt text can be built."""
    errs = []
    chars = {c["name"]: c for c in cast["characters"]}
    lim = st["limits"]
    if len(chars) != len(cast["characters"]):
        errs.append("duplicate character names")
    for n, c in chars.items():
        if not NAME_RE.match(n):
            errs.append("character name must be one upper-case word: %r" % n)
        if not c.get("card"):
            errs.append("character %s has no card" % n)
        for p in c.get("sheet_poses", []):
            if p not in cast["poses"]:
                errs.append("%s sheet_poses: unknown pose %r" % (n, p))
        if len(c.get("sheet_poses", [])) > MAX_SHEET_POSES:
            errs.append("%s: %d sheet_poses (max %d on one model sheet); give a rarely used pose's shots a listed pose"
                        % (n, len(c["sheet_poses"]), MAX_SHEET_POSES))
    # every character a scene shows needs its own model sheet holding every pose it uses: the cast sheet is
    # pasted together from those sheets, so a missing sheet or pose would leave scenes without a reference
    for n in sorted({c["name"] for sh in shots for c in sh.get("characters", []) if c.get("name") in chars}):
        if not chars[n].get("model_sheet"):
            errs.append('character %s is in scenes but has no model sheet: set "model_sheet": true and "sheet_poses"' % n)
            continue
        miss = sorted({c["pose"] for sh in shots for c in sh.get("characters", []) if c["name"] == n}
                      - set(chars[n].get("sheet_poses", [])))
        if miss:
            errs.append("%s: poses used in scenes but missing from sheet_poses: %s" % (n, ", ".join(miss)))
    ids = [s["id"] for s in shots]
    if len(ids) != len(set(ids)):
        errs.append("duplicate shot ids")
    for sh in shots:
        if sh.get("location") not in cast["locations"]:
            errs.append("shot %s: unknown location %r" % (sh["id"], sh.get("location")))
        if len(sh.get("characters", [])) > lim["max_named_characters_per_scene"]:
            errs.append("shot %s: more than %d named characters" % (sh["id"], lim["max_named_characters_per_scene"]))
        for c in sh.get("characters", []):
            if c["name"] not in chars:
                errs.append("shot %s: unknown character %r" % (sh["id"], c["name"]))
            if c.get("pose") not in cast["poses"]:
                errs.append("shot %s: unknown pose %r" % (sh["id"], c.get("pose")))
            if c.get("expression") not in st["expressions"]:
                errs.append("shot %s: unknown expression %r (allowed: %s)" % (sh["id"], c.get("expression"), ", ".join(st["expressions"])))
    return errs


def check(cast, shots, st, items, prompts):
    errs, warns = [], []
    lim = st["limits"]
    sheets = [i for i in items if i["kind"] == "cast_sheet"]
    on_sheet = {tuple(k) for s in sheets for k in s["poses"]}
    heads = {h for s in sheets for h in s["heads"]}
    for sh in shots:
        for c in sh.get("characters", []):
            if (c["name"], c["pose"]) not in on_sheet:
                errs.append("shot %s: pose %s/%s is not on any cast sheet" % (sh["id"], c["name"], c["pose"]))
            if c["expression"] not in heads:
                warns.append("shot %s: expression %s has no head on the cast sheet (budget)" % (sh["id"], c["expression"]))
    if len({n for s in sheets for n in s["characters"]}) > lim["max_characters_per_cast_sheet"]:
        warns.append("more than %d characters on the cast sheet: consistency may drop" % lim["max_characters_per_cast_sheet"])
    for it in items:
        txt = prompts[it["id"]]
        if st["style"] not in txt:
            errs.append("%s: STYLE block missing or altered" % it["id"])
        if len(it["refs"]) > lim["max_refs_per_image"] and not it.get("compose"):  # composed sheets attach nothing
            errs.append("%s: %d references (max %d)" % (it["id"], len(it["refs"]), lim["max_refs_per_image"]))
        if len(txt) > lim["max_prompt_chars"]:
            errs.append("%s: prompt is %d characters (max %d)" % (it["id"], len(txt), lim["max_prompt_chars"]))
        low = txt.lower()
        for bad in st["forbidden"]:
            if bad.lower() in low:
                errs.append("%s: forbidden term %r" % (it["id"], bad))
        if it["kind"] == "scene":
            for line in (st["format_scene"], st["exclusion_scene"]) + ((st["reference_guard"],) if it["refs"] else ()):
                if line not in txt:
                    errs.append("%s: required line missing: %s" % (it["id"], line[:40]))
        for w in it.get("notes", []):
            warns.append("%s: %s" % (it["id"], w))
    return errs, warns


# ---------------------------------------------------------------- outputs
def build(video_dir):
    img = os.path.join(video_dir, "images")
    cast = json.load(open(os.path.join(img, "cast.json"), encoding="utf-8"))
    shots = json.load(open(os.path.join(img, "shots.json"), encoding="utf-8"))["shots"]
    st = load_style(cast.get("style", "stickman-v1"))
    errs = check_refs(cast, shots, st)
    if errs:
        for e in errs:
            print("error:", e)
        sys.exit(1)
    items, info = plan(cast, shots, st)
    by_id = {s["id"]: s for s in shots}
    prompts = {}
    sheet_ids = [i["id"] for i in items if i["kind"] == "cast_sheet"]
    for it in items:
        if it["kind"] == "model_sheet":
            prompts[it["id"]] = model_sheet_prompt(it, cast, st)
        elif it["kind"] == "cast_sheet":
            prompts[it["id"]] = cast_sheet_prompt(it, cast, st)
        else:
            prompts[it["id"]] = scene_prompt(it, by_id[it["id"]], cast, st, sheet_ids)
    return img, cast, shots, st, items, prompts, info


MANUAL_HOW = ("Tạo tay: Google Flow (labs.google/fx/tools/flow), chọn ảnh (Image), model Nano Banana Pro, tỉ lệ 16:9, 2-4 bản; "
              "thêm ảnh tham chiếu theo đúng thứ tự (Add to prompt / ingredients); dán prompt; tải bản lớn nhất; kiểm watermark; "
              "kéo ảnh vào dashboard (nút Tải ảnh lên).")

MD_HEAD = """# Prompt pack: {title}

Style: {style}. Tạo ảnh theo đúng thứ tự dưới đây. Mỗi nhân vật có một model sheet, tạo tay và duyệt trước khi tạo cảnh. Cast sheet không bao giờ tạo: hệ thống tự ghép từ các model sheet đã duyệt.

Cách làm tay (khi không chạy tự động bằng Gemini CLI):
- Google Flow: chọn Image, model Nano Banana Pro (hoặc 2.1), tỉ lệ 16:9. Không dùng Nano Banana 2 Lite (không giữ được nhân vật).
- Đính kèm ảnh tham chiếu đúng thứ tự ghi ở mỗi mục, dán nguyên văn prompt, tải ảnh bản đầy đủ (2K) và lưu đúng tên.
- Phần tiếng Việt chỉ để bạn đọc: không dán vào prompt.

"""


def write(video_dir):
    img, cast, shots, st, items, prompts, info = build(video_dir)
    errs, warns = check(cast, shots, st, items, prompts)
    for w in warns:
        print("warning:", w)
    if errs:
        for e in errs:
            print("error:", e)
        sys.exit(1)
    out = os.path.join(img, "prompts")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.endswith(".txt"):
            os.remove(os.path.join(out, f))
    manifest = []
    md = [MD_HEAD.format(title=cast["title"], style=st["id"])]
    for n, it in enumerate(items, 1):
        fname = "%03d_%s.txt" % (n, it["id"])
        open(os.path.join(out, fname), "w", encoding="utf-8").write(prompts[it["id"]] + "\n")
        entry = dict(it, seq=n, prompt_file="prompts/" + fname, style=st["id"])
        manifest.append(entry)
        attach = ", ".join("%d) %s" % (i, r) for i, r in enumerate(it["refs"], 1)) or "không"
        how = {"manual": (" · TẠO TAY", MANUAL_HOW),
               "compose": (" · TỰ GHÉP", "Không tạo ảnh này: hệ thống tự ghép từ các model sheet ngay khi sheet cuối được duyệt."),
               "agy": (" · tự động (agy)", "Runner tools/gemini/agy_images.py tạo tự động; tạo tay cũng được rồi tải lên.")}[it["route"]]
        md += ["## %d. %s (%s)%s" % (n, it["id"], it["kind"], how[0]),
               "- %s: %s" % ("Ghép từ" if it["route"] == "compose" else "Đính kèm", attach),
               "- %s" % how[1],
               "- Lưu thành: `%s`%s" % (it["save_as"], " (cần duyệt trước khi dùng làm tham chiếu)" if it["approve"] else ""),
               "", "```", prompts[it["id"]], "```", ""]
    json.dump({"video": os.path.basename(os.path.abspath(video_dir)), "style": st["id"], "items": manifest},
              open(os.path.join(out, "manifest.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    open(os.path.join(out, "prompts.md"), "w", encoding="utf-8").write("\n".join(md))
    sheets = [i for i in items if i["kind"] == "cast_sheet"]
    print("%s: %d prompts (%d model sheets, %d cast sheet(s) with %d poses and %d expression heads, %d scenes)"
          % (cast["title"], len(items), sum(i["kind"] == "model_sheet" for i in items), len(sheets),
             sum(len(s["poses"]) for s in sheets), len(info["heads"]), sum(i["kind"] == "scene" for i in items)))


def check_only(video_dir):
    img, cast, shots, st, items, prompts, info = build(video_dir)
    errs, warns = check(cast, shots, st, items, prompts)
    out = os.path.join(img, "prompts")
    if os.path.isdir(out):  # prompt files edited by hand must still carry the style block
        for f in sorted(os.listdir(out)):
            if f.endswith(".txt") and st["style"] not in open(os.path.join(out, f), encoding="utf-8").read():
                errs.append("prompts/%s: STYLE block missing or altered" % f)
    for w in warns:
        print("warning:", w)
    for e in errs:
        print("error:", e)
    print("check: %d errors, %d warnings" % (len(errs), len(warns)))
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if "--check" in sys.argv:
        check_only(sys.argv[1])
    else:
        write(sys.argv[1])
