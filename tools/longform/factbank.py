"""Fact bank of a project: sources, facts with verbatim quotes, saved page text.

  research/sources.json      {"S001": {"id", "title", "publisher", "url", "file", "page_file", "grade", "kind"}}
  research/facts.jsonl       one fact per line (see FIELDS)
  research/pages/NNN.txt     saved page text, first line = URL or file name

A fact is only a fact when its quote is found, verbatim, in the page text that was saved for it. Code checks that
(quote_in_page); a model's word is not enough. Grades follow the spec: A scholarship / museum / heritage agency /
published translation of a primary record, B major newspaper / encyclopedia, C blog / travel / wiki.
"""
import fcntl
import json
import os
import re
import shutil
import time
import unicodedata
from contextlib import contextmanager

STATUSES = ("pending", "verified", "weak", "conflict", "rejected")
NOT_IN_PAGE = "trích không có trong trang đã lưu"
MIN_PART = 12  # each piece of a quote with an inner ellipsis must be at least this long to count
REQUIRED = ("claim_vi", "quote", "url")


def _research(pdir):
    d = os.path.join(pdir, "research")
    os.makedirs(os.path.join(d, "pages"), exist_ok=True)
    return d


@contextmanager
def _locked(pdir):
    with open(os.path.join(_research(pdir), ".bank.lock"), "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def _write(path, text):
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(path + ".tmp", path)


def load(pdir):
    d = _research(pdir)
    try:
        with open(os.path.join(d, "sources.json"), encoding="utf-8") as f:
            sources = json.load(f)
    except (OSError, ValueError):
        sources = {}
    facts = {}
    try:
        with open(os.path.join(d, "facts.jsonl"), encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    fact = json.loads(line)
                    facts[fact["id"]] = fact
    except OSError:
        pass
    return sources, facts


def _save(pdir, sources, facts):
    d = _research(pdir)
    _write(os.path.join(d, "sources.json"), json.dumps(sources, ensure_ascii=False, indent=1))
    _write(os.path.join(d, "facts.jsonl"), "".join(json.dumps(f, ensure_ascii=False) + "\n" for f in facts.values()))


QUOTE_MAP = str.maketrans({"“": '"', "”": '"', "„": '"', "«": '"', "»": '"', "‘": "'", "’": "'", "–": "-", "—": "-"})


def normalise(text):
    t = unicodedata.normalize("NFC", text or "").lower().translate(QUOTE_MAP)
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"^(…|\.\.\.)\s*|\s*(…|\.\.\.)$", "", t).strip()


def quote_in_page(quote, page_text):
    page = normalise(page_text)
    parts = [p.strip() for p in re.split(r"…|\.\.\.", normalise(quote)) if p.strip()]
    if not parts or (len(parts) > 1 and any(len(p) < MIN_PART for p in parts)):
        return False
    pos = 0
    for p in parts:
        i = page.find(p, pos)
        if i < 0:
            return False
        pos = i + len(p)
    return True


def _next_id(prefix, existing):
    n = max([int(k[len(prefix):]) for k in existing if k[len(prefix):].isdigit()], default=0) + 1
    return "%s%03d" % (prefix, n)


def _parse_run(run_dir):
    out = []
    with open(os.path.join(run_dir, "sources.jsonl"), encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                c = json.loads(line)
            except ValueError:
                raise ValueError("sources.jsonl dòng %d không phải JSON" % n)
            missing = [k for k in REQUIRED if not isinstance(c.get(k), str) or not c[k].strip()]
            if missing:
                raise ValueError("sources.jsonl dòng %d thiếu %s" % (n, ", ".join(missing)))
            out.append(c)
    return out


def import_research(pdir, run_dir, origin):
    """Add a research run (sources.jsonl + pages/) to the bank. Raises ValueError, changing nothing, on bad input."""
    claims = _parse_run(run_dir)
    counts = {"sources_added": 0, "facts_added": 0, "rejected": 0, "duplicates": 0}
    with _locked(pdir):
        sources, facts = load(pdir)
        pages_dir = os.path.join(_research(pdir), "pages")
        by_url = {s.get("url") or s.get("file"): sid for sid, s in sources.items()}
        seen = {(f["source"], normalise(f["quote"])) for f in facts.values()}
        copied = {}  # run page path -> bank page path (relative to pdir)
        run_to_bank = {}
        new_facts = []
        for c in claims:
            src_page = os.path.abspath(os.path.join(run_dir, c.get("page_file") or ""))
            page_ok = c.get("page_file") and src_page.startswith(os.path.abspath(run_dir) + os.sep) and os.path.isfile(src_page)
            if page_ok and src_page not in copied:
                nums = [int(p[:3]) for p in os.listdir(pages_dir) if p[:3].isdigit()]
                rel = "research/pages/%03d.txt" % (max(nums, default=0) + 1)
                shutil.copyfile(src_page, os.path.join(pdir, rel))
                copied[src_page] = rel
            page_rel = copied.get(src_page) if page_ok else None
            sid = by_url.get(c["url"])
            if sid is None:
                sid = _next_id("S", sources)
                sources[sid] = {"id": sid, "title": c.get("source_title", ""), "publisher": c.get("author_or_publisher", ""),
                                "url": c["url"], "file": "", "page_file": page_rel or "", "grade": c.get("grade", "C"),
                                "kind": c.get("kind", "other")}
                by_url[c["url"]] = sid
                counts["sources_added"] += 1
            key = (sid, normalise(c["quote"]))
            if key in seen:
                counts["duplicates"] += 1
                continue
            seen.add(key)
            text = open(os.path.join(pdir, page_rel), encoding="utf-8").read() if page_rel else ""
            ok = bool(page_rel) and quote_in_page(c["quote"], text)
            fid = _next_id("F", facts)
            fact = {"id": fid, "claim": c["claim_vi"], "quote": c["quote"], "quote_lang": c.get("quote_lang", ""),
                    "source": sid, "page_file": page_rel or "", "location": c.get("location", ""),
                    "grade": c.get("grade", sources[sid]["grade"]), "reports": c.get("reports", ""),
                    "legend": bool(c.get("legend")), "conflicts_with": list(c.get("conflicts_with") or []),
                    "status": "pending" if ok else "rejected", "checked_by": "" if ok else "code",
                    "check_note": "" if ok else NOT_IN_PAGE, "checked_at": "" if ok else time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "origin": origin}
            facts[fid] = fact
            run_to_bank[c.get("id")] = fid
            new_facts.append(fact)
            counts["facts_added"] += 1
            counts["rejected"] += 0 if ok else 1
        for f in new_facts:
            f["conflicts_with"] = [run_to_bank[x] for x in f["conflicts_with"] if x in run_to_bank]
        _save(pdir, sources, facts)
    return counts


def set_status(pdir, fact_id, status, by, note, grade=None):
    if status not in STATUSES:
        raise ValueError("trạng thái không hợp lệ: %s" % status)
    with _locked(pdir):
        sources, facts = load(pdir)
        if fact_id not in facts:
            raise KeyError(fact_id)
        f = facts[fact_id]
        f.update(status=status, checked_by=by, check_note=note, checked_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
        if grade in ("A", "B", "C"):
            f["grade"] = grade
        _save(pdir, sources, facts)
    return f


def supports_number(facts, sources):
    """A number needs one verified grade-A fact, or verified grade-B facts from two different sources."""
    ok = [f for f in facts if f.get("status") == "verified"]
    if any(f.get("grade") == "A" for f in ok):
        return True
    return len({f["source"] for f in ok if f.get("grade") == "B"}) >= 2
