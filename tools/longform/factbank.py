"""Fact bank of a project: sources, facts with verbatim quotes, saved page text.

  research/sources.json      {"S001": {"id", "title", "publisher", "url", "file", "page_file", "grade", "kind"}}
  research/facts.jsonl       one fact per line (see FIELDS)
  research/pages/NNN.txt     saved page text, first line = URL or file name

A fact is only a fact when its quote is found, verbatim, in the source itself. Studio downloads every web page
itself (fetch) and checks the quote against that download, never against a copy the research worker wrote. When
Studio cannot download a page, the fact stays pending with quote_ok None and the Claude checker must reopen the link. Grades follow the spec: A scholarship / museum / heritage agency /
published translation of a primary record, B major newspaper / encyclopedia, C blog / travel / wiki.
"""
import fcntl
import html
import json
import os
import re
import time
import unicodedata
import urllib.request
from contextlib import contextmanager
from html.parser import HTMLParser

STATUSES = ("pending", "verified", "weak", "conflict", "rejected")
NOT_IN_PAGE = "trích không có trong trang đã lưu"
NO_FETCH = "Studio không tải được trang gốc; Claude phải mở lại link để đối chiếu"
UPLOAD_NOTE = "file tải lên không đọc được bằng code; Claude phải mở file để đối chiếu"
MIN_PART = 12  # each piece of a quote with an inner ellipsis must be at least this long to count
MIN_QUOTE, MIN_WORDS = 20, 4  # a quote shorter than this proves nothing
USABLE = ("verified", "weak", "conflict")
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
    q = normalise(quote)
    if len(q) < MIN_QUOTE or len(q.split()) < MIN_WORDS:
        return False
    parts = [p.strip() for p in re.split(r"…|\.\.\.", q) if p.strip()]
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


class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "head", "svg"}
    BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr", "td", "section", "article", "blockquote"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def fetch(url, timeout=20):
    """Readable text of a web page downloaded by Studio itself, or None when it cannot be downloaded."""
    if not re.match(r"^https?://", url or ""):
        return None
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Studio fact check)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(8 * 1024 * 1024)
            charset = r.headers.get_content_charset() or "utf-8"
            ctype = r.headers.get_content_type()
    except Exception:  # noqa: BLE001  any network or HTTP problem means "could not check here"
        return None
    text = raw.decode(charset, "replace")
    if ctype in ("text/html", "application/xhtml+xml") or "<html" in text[:2000].lower():
        p = _Text()
        p.feed(text)
        text = html.unescape("".join(p.out))
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip() or None


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
            if not isinstance(c, dict):
                raise ValueError("sources.jsonl dòng %d không phải object" % n)
            missing = [k for k in REQUIRED if not isinstance(c.get(k), str) or not c[k].strip()]
            if missing:
                raise ValueError("sources.jsonl dòng %d thiếu %s" % (n, ", ".join(missing)))
            cw = c.get("conflicts_with") or []
            if not isinstance(cw, list) or not all(isinstance(x, str) for x in cw):
                raise ValueError("sources.jsonl dòng %d: conflicts_with phải là danh sách mã" % n)
            if c.get("grade") not in (None, "A", "B", "C"):
                raise ValueError("sources.jsonl dòng %d: hạng nguồn phải là A, B hoặc C" % n)
            out.append(c)
    return out


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def import_research(pdir, run_dir, origin):
    """Add a research run (sources.jsonl + pages/) to the bank. Raises ValueError, changing nothing, on bad input.

    Web quotes are checked against Studio's own download of the URL. An uploaded TXT is checked against the file; a
    PDF or image upload, or a page Studio cannot download, stays pending for Claude to reopen (quote_ok None).
    """
    claims = _parse_run(run_dir)
    run_abs = os.path.realpath(run_dir)
    counts = {"sources_added": 0, "facts_added": 0, "rejected": 0, "duplicates": 0}
    downloads = {}
    for url in {c["url"] for c in claims}:
        downloads[url] = fetch(url)  # network outside the lock
    with _locked(pdir):
        sources, facts = load(pdir)
        pages_dir = os.path.join(_research(pdir), "pages")
        by_url = {s.get("url") or s.get("file"): sid for sid, s in sources.items()}
        by_key = {(f["source"], normalise(f["quote"])): f["id"] for f in facts.values()}
        saved = {}  # text key -> bank page path (relative to pdir)

        def save_page(first_line, text):
            key = (first_line, text)
            if key not in saved:
                nums = [int(p[:3]) for p in os.listdir(pages_dir) if p[:3].isdigit()]
                rel = "research/pages/%03d.txt" % (max(nums, default=0) + 1)
                with open(os.path.join(pdir, rel), "w", encoding="utf-8") as f:
                    f.write(first_line + "\n" + text)
                saved[key] = rel
            return saved[key]

        run_to_bank, new_facts = {}, []
        for c in claims:
            url = c["url"]
            sid = by_url.get(url)
            if sid is not None and (sid, normalise(c["quote"])) in by_key:
                run_to_bank[c.get("id")] = by_key[(sid, normalise(c["quote"]))]
                counts["duplicates"] += 1
                continue
            # where the quote is checked
            page_rel, page_by, quote_ok, note = "", "", False, NOT_IN_PAGE
            if downloads.get(url):
                page_rel, page_by = save_page(url, downloads[url]), "studio"
                quote_ok = quote_in_page(c["quote"], downloads[url])
            elif url.startswith("file:"):
                up = os.path.join(_research(pdir), "uploads", os.path.basename(url[5:]))
                if os.path.isfile(up):
                    page_by, page_rel = "upload", os.path.relpath(up, pdir)
                    text = _read(up) if up.lower().endswith(".txt") else None
                    quote_ok = quote_in_page(c["quote"], text) if text is not None else None
                    note = UPLOAD_NOTE if quote_ok is None else note
            else:
                agy_page = os.path.realpath(os.path.join(run_dir, c.get("page_file") or ""))
                text = _read(agy_page) if c.get("page_file") and agy_page.startswith(run_abs + os.sep) else None
                if text is not None and quote_in_page(c["quote"], text):
                    page_rel, page_by, quote_ok, note = save_page(url, text.split("\n", 1)[-1]), "agy", None, NO_FETCH
            if sid is None:
                sid = _next_id("S", sources)
                sources[sid] = {"id": sid, "title": c.get("source_title", ""), "publisher": c.get("author_or_publisher", ""),
                                "url": url, "file": url[5:] if url.startswith("file:") else "", "page_file": page_rel,
                                "grade": c.get("grade") or "C", "kind": c.get("kind", "other")}
                by_url[url] = sid
                counts["sources_added"] += 1
            ok = quote_ok is not False
            fid = _next_id("F", facts)
            fact = {"id": fid, "claim": c["claim_vi"], "quote": c["quote"], "quote_lang": c.get("quote_lang", ""),
                    "source": sid, "page_file": page_rel, "page_by": page_by, "quote_ok": quote_ok,
                    "location": c.get("location", ""), "grade": c.get("grade") or sources[sid]["grade"],
                    "reports": c.get("reports", ""), "legend": bool(c.get("legend")),
                    "conflicts_with": list(c.get("conflicts_with") or []),
                    "status": "pending" if ok else "rejected", "checked_by": "" if quote_ok is not False else "code",
                    "check_note": "" if quote_ok else note, "checked_at": "" if ok else time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "origin": origin}
            facts[fid] = fact
            by_key[(sid, normalise(c["quote"]))] = fid
            run_to_bank[c.get("id")] = fid
            new_facts.append(fact)
            counts["facts_added"] += 1
            counts["rejected"] += 0 if ok else 1
        for f in new_facts:  # run ids -> bank ids, and every link mirrored on its partner
            f["conflicts_with"] = sorted({run_to_bank[x] for x in f["conflicts_with"] if x in run_to_bank} - {f["id"]})
        for f in new_facts:
            for other in f["conflicts_with"]:
                partner = facts[other]
                if f["id"] not in partner["conflicts_with"]:
                    partner["conflicts_with"] = sorted(partner["conflicts_with"] + [f["id"]])
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
        if status in USABLE and f.get("quote_ok") is False:
            raise ValueError("dữ kiện %s: trích không có trong trang gốc, không thể đánh dấu là dùng được" % fact_id)
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
