import json
import os
import shutil
import tempfile
import unittest

from tools.longform import factbank

PAGE1 = "https://example.org/toan-thu\nNăm Mậu Tý, mùa xuân, tháng 3, ngày 8, quân Nguyên đến sông Bạch Đằng.\nHưng Đạo Vương đã cho cắm cọc ở sông."
PAGE2 = "https://news.example/coc\nCác nhà khảo cổ tìm thấy bãi cọc Yên Giang năm 1958."


def claim(i, quote, url, page, **kw):
    c = {"id": i, "topic": 5, "claim_vi": "claim " + i, "quote": quote, "quote_lang": "vi", "source_title": "T " + url,
         "author_or_publisher": "P", "url": url, "page_file": page, "location": "", "grade": "A",
         "kind": "primary_record", "reports": "Toàn thư", "legend": False, "conflicts_with": [], "notes": ""}
    c.update(kw)
    return c


class FactbankTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.pdir = os.path.join(self.root, "projects", "001-x")
        os.makedirs(os.path.join(self.pdir, "research"))
        self.run = os.path.join(self.root, "run")
        os.makedirs(os.path.join(self.run, "pages"))
        open(os.path.join(self.run, "pages", "001.txt"), "w").write(PAGE1)
        open(os.path.join(self.run, "pages", "002.txt"), "w").write(PAGE2)

    def tearDown(self):
        shutil.rmtree(self.root)

    def write_run(self, claims):
        with open(os.path.join(self.run, "sources.jsonl"), "w") as f:
            for c in claims:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")

    def test_normalise_quotes_and_space(self):
        self.assertEqual(factbank.normalise("  “Quân  Nguyên”\n đến…"), '"quân nguyên" đến')

    def test_quote_in_page_exact(self):
        self.assertTrue(factbank.quote_in_page("quân Nguyên đến sông Bạch Đằng", PAGE1))
        self.assertFalse(factbank.quote_in_page("quân Nguyên thua ở sông Hồng", PAGE1))

    def test_quote_in_page_with_ellipsis(self):
        self.assertTrue(factbank.quote_in_page("Năm Mậu Tý, mùa xuân … Hưng Đạo Vương đã cho cắm cọc", PAGE1))
        self.assertFalse(factbank.quote_in_page("Hưng Đạo Vương đã cho cắm cọc … Năm Mậu Tý, mùa xuân", PAGE1))  # order
        self.assertFalse(factbank.quote_in_page("Năm … cọc", PAGE1))  # parts too short to mean anything

    def test_quote_not_in_page_rejected(self):
        self.write_run([claim("S001", "Quân Nguyên bị đánh tan hoàn toàn trên sông", "https://example.org/toan-thu", "pages/001.txt")])
        out = factbank.import_research(self.pdir, self.run, "run-1")
        self.assertEqual(out["rejected"], 1)
        _, facts = factbank.load(self.pdir)
        f = facts["F001"]
        self.assertEqual(f["status"], "rejected")
        self.assertEqual(f["check_note"], "trích không có trong trang đã lưu")

    def test_missing_page_rejected(self):
        self.write_run([claim("S001", "quân Nguyên đến sông Bạch Đằng", "https://example.org/toan-thu", "pages/404.txt")])
        factbank.import_research(self.pdir, self.run, "run-1")
        self.assertEqual(factbank.load(self.pdir)[1]["F001"]["status"], "rejected")

    def test_import_counts(self):
        self.write_run([claim("S001", "quân Nguyên đến sông Bạch Đằng", "https://example.org/toan-thu", "pages/001.txt"),
                        claim("S002", "bãi cọc Yên Giang năm 1958", "https://news.example/coc", "pages/002.txt", grade="B")])
        out = factbank.import_research(self.pdir, self.run, "run-1")
        self.assertEqual(out, {"sources_added": 2, "facts_added": 2, "rejected": 0, "duplicates": 0})
        sources, facts = factbank.load(self.pdir)
        self.assertEqual(sorted(sources), ["S001", "S002"])
        f = facts["F002"]
        self.assertEqual((f["status"], f["source"], f["origin"], f["claim"]), ("pending", "S002", "run-1", "claim S002"))
        page = sources[f["source"]]["page_file"]
        self.assertTrue(os.path.isfile(os.path.join(self.pdir, page)))
        self.assertTrue(page.startswith("research/pages/"))

    def test_reimport_dedupes(self):
        c = [claim("S001", "quân Nguyên đến sông Bạch Đằng", "https://example.org/toan-thu", "pages/001.txt")]
        self.write_run(c)
        factbank.import_research(self.pdir, self.run, "run-1")
        c[0]["quote"] = "Quân  Nguyên đến sông Bạch Đằng"  # same quote, other spacing
        self.write_run(c + [claim("S002", "Hưng Đạo Vương đã cho cắm cọc ở sông", "https://example.org/toan-thu", "pages/001.txt")])
        out = factbank.import_research(self.pdir, self.run, "run-2")
        self.assertEqual((out["sources_added"], out["facts_added"], out["duplicates"]), (0, 1, 1))
        sources, facts = factbank.load(self.pdir)
        self.assertEqual(len(sources), 1)
        self.assertEqual(len(facts), 2)

    def test_conflicts_rewritten(self):
        self.write_run([claim("S010", "quân Nguyên đến sông Bạch Đằng", "https://example.org/toan-thu", "pages/001.txt", conflicts_with=["S011"]),
                        claim("S011", "bãi cọc Yên Giang năm 1958", "https://news.example/coc", "pages/002.txt", conflicts_with=["S010"])])
        factbank.import_research(self.pdir, self.run, "run-1")
        _, facts = factbank.load(self.pdir)
        self.assertEqual(facts["F001"]["conflicts_with"], ["F002"])
        self.assertEqual(facts["F002"]["conflicts_with"], ["F001"])

    def test_bad_line_changes_nothing(self):
        self.write_run([claim("S001", "quân Nguyên đến sông Bạch Đằng", "https://example.org/toan-thu", "pages/001.txt")])
        factbank.import_research(self.pdir, self.run, "run-1")
        with open(os.path.join(self.run, "sources.jsonl"), "a") as f:
            f.write('{"id": "S009", "quote": ""}\n')
        with self.assertRaises(ValueError):
            factbank.import_research(self.pdir, self.run, "run-2")
        with open(os.path.join(self.run, "sources.jsonl"), "w") as f:
            f.write("{not json\n")
        with self.assertRaises(ValueError):
            factbank.import_research(self.pdir, self.run, "run-3")
        sources, facts = factbank.load(self.pdir)
        self.assertEqual((len(sources), len(facts)), (1, 1))

    def test_set_status(self):
        self.write_run([claim("S001", "quân Nguyên đến sông Bạch Đằng", "https://example.org/toan-thu", "pages/001.txt")])
        factbank.import_research(self.pdir, self.run, "run-1")
        f = factbank.set_status(self.pdir, "F001", "verified", "claude", "khớp")
        self.assertEqual((f["status"], f["checked_by"], f["check_note"]), ("verified", "claude", "khớp"))
        self.assertTrue(f["checked_at"])
        with self.assertRaises(ValueError):
            factbank.set_status(self.pdir, "F001", "great", "x", "")
        with self.assertRaises(KeyError):
            factbank.set_status(self.pdir, "F999", "verified", "x", "")

    def test_supports_number(self):
        S = {"S1": {"grade": "A"}, "S2": {"grade": "B"}, "S3": {"grade": "B"}, "S4": {"grade": "C"}}
        f = lambda src, st="verified", grade=None: {"source": src, "status": st, "grade": grade or S[src]["grade"]}
        self.assertTrue(factbank.supports_number([f("S1")], S))
        self.assertFalse(factbank.supports_number([f("S2")], S))
        self.assertFalse(factbank.supports_number([f("S2"), f("S2")], S))
        self.assertTrue(factbank.supports_number([f("S2"), f("S3")], S))
        self.assertFalse(factbank.supports_number([f("S4"), f("S4")], S))
        self.assertFalse(factbank.supports_number([f("S1", "pending")], S))


if __name__ == "__main__":
    unittest.main()
