#!/usr/bin/env python3
"""Compare candidate image styles before one is locked: the same model sheets, one prompt per style.

Usage:
  style_test.py TEST_DIR   reads TEST_DIR/cast.json (characters with "model_sheet": true and their poses) and every
                           TEST_DIR/styles/*.json; writes TEST_DIR/prompts/<style>_<character>.txt and prompts.md

The prompts come from make_prompts.model_sheet_prompt, so they are exactly what the generator will write once the
winning style is copied to tools/imageprompts/style/<id>.json. Exit 1 when a prompt breaks a style rule.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_prompts as mp  # noqa: E402

KEYS = ["id", "style", "animals", "background_people", "setting_style", "sheet_background", "format_scene",
        "exclusion_scene", "reference_guard", "history_line", "label_style", "expressions", "turnaround", "forbidden", "limits"]


def run(test_dir):
    cast = json.load(open(os.path.join(test_dir, "cast.json"), encoding="utf-8"))
    styles = [json.load(open(p, encoding="utf-8")) for p in sorted(glob.glob(os.path.join(test_dir, "styles", "*.json")))]
    errs = []
    if not styles:
        errs.append("no styles in %s/styles" % test_dir)
    chars = [c for c in cast["characters"] if c.get("model_sheet")]
    for c in chars:
        if not mp.NAME_RE.match(c["name"]):
            errs.append("character name must be one upper-case word: %r" % c["name"])
        errs += ["%s: unknown pose %r" % (c["name"], p) for p in c.get("sheet_poses", []) if p not in cast["poses"]]
        if len(c.get("sheet_poses", [])) > mp.MAX_SHEET_POSES:
            errs.append("%s: more than %d sheet_poses" % (c["name"], mp.MAX_SHEET_POSES))
    prompts = {}
    for st in styles:
        errs += ["%s: missing key %r" % (st.get("id"), k) for k in KEYS if k not in st]
        if len(st.get("turnaround", [])) not in mp.NUM_WORDS:
            errs.append("%s: turnaround needs 3 to 8 views" % st.get("id"))
        if errs:
            continue
        for c in chars:
            txt = mp.model_sheet_prompt({"character": c["name"]}, cast, st)
            low = txt.lower()
            errs += ["%s/%s: forbidden term %r" % (st["id"], c["name"], b) for b in st["forbidden"] if b.lower() in low]
            if len(txt) > st["limits"]["max_prompt_chars"]:
                errs.append("%s/%s: prompt is %d characters" % (st["id"], c["name"], len(txt)))
            prompts[(st["id"], c["name"])] = txt
    if errs:
        for e in errs:
            print("error:", e)
        sys.exit(1)
    out = os.path.join(test_dir, "prompts")
    os.makedirs(out, exist_ok=True)
    for f in glob.glob(os.path.join(out, "*.txt")):  # prompts of styles or characters removed since the last run
        os.remove(f)
    md = ["# Style test: %s" % cast["title"], "",
          "Mỗi nhân vật có một prompt cho từng style. Tạo trên Google Flow: Image, Nano Banana Pro, tỉ lệ 16:9, "
          "không đính kèm ảnh nào, dán nguyên văn prompt, 2 bản mỗi prompt. So sánh: nhân vật có giống nhau giữa các "
          "góc nhìn và biểu cảm không, mặt có rõ không, có hợp kinh dị và TikTok không. Phần tiếng Việt không dán vào prompt.", ""]
    if cast.get("story"):
        md += ["Nguồn: " + cast["story"], ""]
    for c in chars:
        md += ["## %s" % c["name"], ""]
        for st in styles:
            fname = "%s_%s.txt" % (st["id"], c["name"].lower())
            open(os.path.join(out, fname), "w", encoding="utf-8").write(prompts[(st["id"], c["name"])] + "\n")
            md += ["### %s (`prompts/%s`)" % (st["id"], fname), "", "```", prompts[(st["id"], c["name"])], "```", ""]
    open(os.path.join(out, "prompts.md"), "w", encoding="utf-8").write("\n".join(md))
    print("%d styles x %d characters = %d prompts in %s" % (len(styles), len(chars), len(prompts), out))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    run(sys.argv[1])
