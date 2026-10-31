"""agy image jobs: generate one image item, check it by machine, upscale it, then have agy review it.

  python -m tools.longform.image_worker generate <project> <item>
  python -m tools.longform.image_worker review <project> <item>

Studio runs these as jobs on the agy lane (kinds agy_image and agy_image_review). The worker is plain Python that
calls the agy CLI itself (imagegen.generate, agy.argv); it never goes through Claude and never skips permissions.
Each image is reviewed as soon as it exists: generate enqueues its own review, so nothing waits for a batch.
"""
import collections
import hashlib
import os
import sys
import tempfile

from PIL import Image

from tools.longform import claude_box, cutout, imagegen, images, inbox, jobs, paths, upscale

PY = os.path.join(paths.WS, ".venv", "bin", "python")
MIN_LONG_SIDE = 1024
MAX_CHECK_FAILS = 3
THUMB = 256
FIGURE_SHARE = 0.02  # an opaque blob bigger than this share of all opaque pixels counts as a figure
CUTOUT_VI = {"no transparency": "không tách được nền xanh", "touches edge": "nhân vật chạm mép ảnh",
             "key colour left on figure": "còn màu xanh nền trên người nhân vật"}


def _pdir(pid):
    if claude_box.check_project(pid) is None:
        raise ValueError("thiếu dự án")
    return os.path.join(paths.projects(), pid)


def _build(action):
    def build(params):
        pdir = _pdir(params.get("project"))
        try:
            images.get(pdir, params.get("item"))
        except KeyError:
            raise ValueError("không có ảnh %s" % params.get("item"))
        return [PY, "-m", "tools.longform.image_worker", action, params["project"], params["item"]]
    return build


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _blobs(im):
    """Sizes of the 4-connected opaque regions of a green-screen thumbnail (None when the border is not green)."""
    key = cutout._border_key(im)
    if key[1] < max(key[0], key[2]) + 40:
        return None
    w, h = im.size
    solid = [a >= cutout.SOLID for a in cutout._mask(im, key, 60)]
    seen = bytearray(w * h)
    sizes = []
    for start in range(w * h):
        if seen[start] or not solid[start]:
            continue
        n, q = 0, collections.deque([start])
        seen[start] = 1
        while q:
            i = q.popleft()
            n += 1
            x, y = i % w, i // w
            for j in (i - 1 if x else -1, i + 1 if x < w - 1 else -1, i - w if y else -1, i + w if y < h - 1 else -1):
                if j >= 0 and not seen[j] and solid[j]:
                    seen[j] = 1
                    q.append(j)
        sizes.append(n)
    return sizes


def _pose_checks(path):
    im = Image.open(path).convert("RGB")
    im.thumbnail((THUMB, THUMB))
    sizes = _blobs(im)
    if sizes is None:
        return [("nền không phải màu xanh chroma #00B140", "The background must be flat chroma green #00B140 filling the whole frame.")]
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        src, cut = os.path.join(tmp, "thumb.png"), os.path.join(tmp, "cut.png")
        im.save(src)
        try:
            cutout.cut(src, cut)
            for p in cutout.check(cut, source=src):
                vi = next((v for k, v in CUTOUT_VI.items() if p.startswith(k)), p)
                out.append((vi, "Clean cutout needed: %s. Keep the whole figure inside the frame with green around it." % p))
        except ValueError:
            out.append(("không tách được nhân vật khỏi nền xanh", "Draw one clear figure on flat chroma green #00B140."))
    total = sum(sizes)
    figures = [s for s in sizes if total and s > FIGURE_SHARE * total]
    if len(figures) > 1:
        out.append(("ảnh có %d hình người, chỉ được một nhân vật" % len(figures),
                    "Draw exactly one figure, one single pose: not a sheet, no second view, no extra people."))
    return out


def _checks(item, path, pdir):
    """(Vietnamese problem, English prompt fix) pairs."""
    out = []
    w, h = Image.open(path).size
    if max(w, h) < MIN_LONG_SIDE:
        out.append(("ảnh nhỏ quá (%dx%d), cạnh dài cần ít nhất %d px" % (w, h, MIN_LONG_SIDE),
                    "Generate the image at full size."))
    digest = _sha(path)
    for other in images.load(pdir):
        raw = (other.get("files") or {}).get("raw")
        if other["id"] != item["id"] and raw and os.path.isfile(images.abspath(raw)) and _sha(images.abspath(raw)) == digest:
            out.append(("ảnh trùng hệt ảnh %s" % other["id"], "Draw a new image; do not repeat an earlier one."))
            break
    if item["type"] == "pose":
        out += _pose_checks(path)
    return out


def check_raw(item, path, pdir=None):
    """Vietnamese problems of a raw agy image, found by code before any AI review."""
    pdir = pdir or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(path))))
    return [vi for vi, _ in _checks(item, path, pdir)]


def _wait(pdir, item_id, problems, text):
    pid = os.path.basename(pdir)
    it = images.update(pdir, item_id, state="wait", problems=problems, note=text)
    inbox.add(pid, "image_review", "%s %s" % (item_id, text), screen="images", key="img:%s:%s" % (pid, item_id))
    return it


def _upscale(item, raw, pdir):
    """Upscale into images/final (pose: also the cutout into images/cutout). Returns (files, problems)."""
    iid = item["id"]
    final_dir, cut_dir = os.path.join(pdir, "images", "final"), os.path.join(pdir, "images", "cutout")
    os.makedirs(final_dir, exist_ok=True)
    final = os.path.join(final_dir, iid + ".png")
    rw, rh = Image.open(raw).size
    if item["type"] == "bg":
        want = upscale.BG_SIZE
        size = upscale.upscale(raw, final, size=want)
    else:
        want = (rw * 2, rh * 2)
        size = upscale.upscale(raw, final, scale=2)
    files = {"raw": images.rel(raw), "final": images.rel(final), "cutout": None}
    if tuple(size)[0] < want[0] or tuple(size)[1] < want[1]:
        return files, [("ảnh phóng to chỉ đạt %dx%d, cần %dx%d" % (tuple(size) + tuple(want)), "Generate the image at full size.")]
    if item["type"] == "pose":
        os.makedirs(cut_dir, exist_ok=True)
        cut = os.path.join(cut_dir, iid + ".png")
        try:
            cutout.cut(final, cut)
        except ValueError:
            return files, [("không tách được nhân vật khỏi nền xanh", "Draw one clear figure on flat chroma green #00B140.")]
        files["cutout"] = images.rel(cut)
    return files, []


def generate_item(pdir, item_id):
    pid = os.path.basename(pdir)
    it = images.update(pdir, item_id, state="generating", note="lần %d" % (images.get(pdir, item_id)["attempts"] + 1))
    prompt = it["prompt"]
    if it.get("fix"):
        prompt += "\n\nFIX (the previous image was rejected; correct this):\n" + it["fix"]
    refs = [images.abspath(r) for r in it.get("refs") or []]
    aspect = "9:16" if it["type"] == "pose" else "16:9"
    try:
        raw = imagegen.generate(prompt, refs, os.path.join(pdir, "images", "raw"), item_id, aspect)[0]
    except imagegen.QuotaExhausted:
        jobs.set_paused(True, "agy hết quota")
        inbox.add(pid, "quota", "agy hết lượt tạo ảnh; Studio đã tạm dừng", screen="images", key="quota:agy")
        return images.update(pdir, item_id, state="queued", note="agy hết quota")
    found = _checks(it, raw, pdir)
    files = {"raw": images.rel(raw), "final": None, "cutout": None}
    if not found:
        files, found = _upscale(it, raw, pdir)
    if found:
        attempts = it["attempts"] + 1
        vi, en = [p for p, _ in found], " ".join(dict.fromkeys(f for _, f in found))
        images.update(pdir, item_id, attempts=attempts, problems=vi, fix=en, files=files)
        if attempts >= MAX_CHECK_FAILS:
            return _wait(pdir, item_id, vi, "kiểm máy trượt %d lần: %s" % (attempts, "; ".join(vi)))
        it = images.update(pdir, item_id, state="queued", note="kiểm máy: " + "; ".join(vi))
        jobs.enqueue("agy_image", {"project": pid, "item": item_id}, pid, "agy vẽ lại %s" % item_id)
        return it
    it = images.update(pdir, item_id, state="reviewing", files=files, problems=[], score=None)
    jobs.enqueue("agy_image_review", {"project": pid, "item": item_id}, pid, "agy chấm %s" % item_id)
    return it


def review_item(pdir, item_id):
    raise NotImplementedError


def job_end(job):
    """A worker that crashed or was stopped leaves its item mid-way: mark it failed so the owner sees it."""
    if job["status"] == "done":
        return
    try:
        pdir = _pdir(job["params"].get("project"))
        it = images.get(pdir, job["params"].get("item"))
    except (KeyError, ValueError):
        return
    if it["state"] in ("generating", "reviewing"):
        images.update(pdir, it["id"], state="failed", problems=it.get("problems") or ["job %s dừng giữa chừng" % job["kind"]],
                      note="job %s" % job["status"])


def main(argv):
    action, pid, item_id = argv
    pdir = _pdir(pid)
    try:
        if action == "generate":
            generate_item(pdir, item_id)
        elif action == "review":
            review_item(pdir, item_id)
        else:
            raise ValueError("không có lệnh %s" % action)
    except Exception as e:  # noqa: BLE001  the item shows why; the job fails and reaches the inbox
        images.update(pdir, item_id, state="failed", problems=["lỗi: %s" % e], note=action)
        print("lỗi: %s" % e, flush=True)
        return 1
    return 0


jobs.register(jobs.Kind("agy_image", "agy", _build("generate"), on_end=job_end))
jobs.register(jobs.Kind("agy_image_review", "agy", _build("review"), on_end=job_end))

if __name__ == "__main__":
    from tools.longform import image_worker
    sys.exit(image_worker.main(sys.argv[1:]))
