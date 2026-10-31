# Verify facts for "$title"

You are the independent fact checker (you did not write these facts). For each fact below, open its saved page
file, find the quote, and decide whether the quote really says the claim.

Rules:
- `verified`: the quote is in the page and states the claim (numbers, names and dates must match exactly).
- `weak`: the quote supports the claim only partly or vaguely, or the source is grade C.
- `rejected`: the quote is not in the page, or it does not support the claim.
- Re-grade the source with the spec scale: A = scholarship, museum, heritage agency, archaeological report, or a
  published translation of a primary record; B = major newspaper or encyclopedia; C = blog, travel site, wiki.
- `note`: one short Vietnamese sentence saying why.

Facts (JSON): `facts.json` in this folder. Page files are under `$project_dir`.

Write `result.json` in this folder with the Write tool, and do nothing else:

```json
[{"id": "F001", "status": "verified|weak|rejected", "grade": "A|B|C", "note": "…"}]
```

Include every fact id from `facts.json`, once each.
