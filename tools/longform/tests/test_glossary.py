"""Per-language glossary: seeded name readings (checked: false), lookup and consistency check."""
import os
import shutil
import tempfile
import unicodedata
import unittest

WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class GlossaryTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        shutil.copytree(os.path.join(WS, "library", "glossary"), os.path.join(self.root, "library", "glossary"))
        os.environ["LONGFORM_ROOT"] = self.root
        from tools.longform import glossary
        self.g = glossary

    def tearDown(self):
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def test_seed_ja_tran_hung_dao(self):
        t = self.g.load("ja")
        self.assertEqual(t["lang"], "ja")
        row = [n for n in t["names"] if n["vi"] == "Trần Hưng Đạo"][0]
        self.assertEqual(row["target"], "チャン・フン・ダオ")
        self.assertFalse(row["checked"])
        for lang in ("en", "ja", "de", "es"):
            t = self.g.load(lang)
            self.assertEqual(len(t["names"]), 9, lang)
            self.assertTrue(all(n["checked"] is False for n in t["names"]), lang)
        self.assertEqual([n["target"] for n in self.g.load("de")["names"] if n["vi"] == "Bạch Đằng"], ["Bach-Dang-Fluss"])

    def test_expected_and_check(self):
        texts = ["Rồi quân Nguyên đến sông Bạch Đằng.", "Trần Hưng Đạo cho đóng cọc."]
        self.assertEqual(sorted(self.g.expected("en", texts)),
                         [("Bạch Đằng", "Bach Dang River"), ("Trần Hưng Đạo", "Tran Hung Dao")])
        self.assertEqual(self.g.check("en", texts, "TRAN HUNG DAO waited at the Bach Dang River."), [])
        miss = self.g.check("en", texts, "Tran Hung Dao waited at the river.")
        self.assertEqual(len(miss), 1)
        self.assertIn("Bach Dang River", miss[0])
        # NFC: a decomposed accent in the target text still matches
        self.g.add("es", "Ô Mã Nhi", "Ô Mã Nhi")
        self.assertEqual(self.g.check("es", ["Ô Mã Nhi"], unicodedata.normalize("NFD", "Ô Mã Nhi llegó")), [])

    def test_add_dedupes(self):
        n = len(self.g.load("en")["names"])
        self.g.add("en", "Phạm Ngũ Lão", "Pham Ngu Lao")
        self.g.add("en", "Phạm Ngũ Lão", "Pham Ngu Lao (general)")
        names = self.g.load("en")["names"]
        self.assertEqual(len(names), n + 1)
        row = [x for x in names if x["vi"] == "Phạm Ngũ Lão"][0]
        self.assertEqual(row["target"], "Pham Ngu Lao (general)")
        self.assertFalse(row["checked"])
        self.g.add("en", "cọc gỗ", "wooden stakes", kind="terms")
        self.assertEqual([x["target"] for x in self.g.load("en")["terms"]], ["wooden stakes"])
        with self.assertRaises(ValueError):
            self.g.add("en", "x", "y", kind="other")

    def test_confirm(self):
        self.g.confirm("ja", "Thăng Long")
        row = [x for x in self.g.load("ja")["names"] if x["vi"] == "Thăng Long"][0]
        self.assertTrue(row["checked"])
        with self.assertRaises(KeyError):
            self.g.confirm("ja", "không có")


if __name__ == "__main__":
    unittest.main()
