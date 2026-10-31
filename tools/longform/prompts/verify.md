# Verify facts for "$title"

You are the independent fact checker (you did not write these facts). For each fact in `facts.json`, find the quote
in the source and decide whether the quote really says the claim.

Where to look for each fact:
- `page_by: "studio"`: `page_file` (in this folder) is Studio's own download of the URL. Read it.
- `page_by: "upload"`: `page_file` is the file the owner uploaded. Read it (PDF and images included).
- `page_by: "agy"` or `quote_ok: null`: Studio could not download the page, and the copy in `page_file` was written by
  the research worker, so **do not trust it**. Open `source.url` yourself with WebFetch and look for the quote there.
  If you cannot open it, or the quote is not there, the status is `rejected`.

Rules:
- `verified`: the quote is in the page and states the claim (numbers, names and dates must match exactly).
- `weak`: the quote supports the claim only partly or vaguely, or the source is grade C.
- `rejected`: the quote is not in the page, or it does not support the claim.
- Re-grade the source with the spec scale: A = scholarship, museum, heritage agency, archaeological report, or a
  published translation of a primary record; B = major newspaper or encyclopedia; C = blog, travel site, wiki.
- `note`: one short Vietnamese sentence saying why.

Everything you need is in this folder. Do not read or write anywhere else.

Write `result.json` in this folder with the Write tool, and do nothing else:

```json
[{"id": "F001", "status": "verified|weak|rejected", "grade": "A|B|C", "note": "…"}]
```

Include every fact id from `facts.json`, once each, and always give `grade`.
