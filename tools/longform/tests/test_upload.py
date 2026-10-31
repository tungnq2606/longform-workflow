"""Upload texts per language: validation (no links, no AI line, one sources line), chapters, upload.md, agy job."""
import json
import os

from tools.longform.tests.test_workers import Base, claim

DESC_EN = "How a river beat a fleet in 1288.\n\nSources: Đại Việt sử ký toàn thư, Yuan shi"


def texts(**kw):
    t = {"title": "How Vietnam Beat the Mongol Fleet", "description": DESC_EN, "tags": ["history", "vietnam", "mongols"]}
    t.update(kw)
    return t


def doc(lang):
    return {"lang": lang, "chapters": [
        {"id": "C01", "title": "The hook", "beats": [{"id": "B01", "goal": "g", "sentences": [
            {"id": "s001", "text": "Quân Nguyên đến sông Bạch Đằng.", "facts": ["F001"], "kind": "fact", "note": ""}]}]},
        {"id": "C02", "title": "The stakes", "beats": [{"id": "B02", "goal": "g", "sentences": [
            {"id": "s002", "text": "Bạn đoán xem?", "facts": [], "kind": "question", "note": ""}]}]},
        {"id": "C03", "title": "The battle", "beats": [{"id": "B03", "goal": "g", "sentences": [
            {"id": "s003", "text": "Rồi sao nữa?", "facts": [], "kind": "question", "note": ""}]}]}]}


class UploadTest(Base):
    def setUp(self):
        super().setUp()
        from tools.longform import progress, upload
        self.up, self.progress = upload, progress

    def test_refuses_links_and_ai_line(self):
        self.assertEqual(self.up.validate(texts(), "en"), [])
        self.assertTrue(self.up.validate(texts(description=DESC_EN + "\nMore: https://example.org"), "en"))
        self.assertTrue(self.up.validate(texts(description="Video minh họa bằng AI.\n" + DESC_EN), "en"))
        self.assertTrue(self.up.validate(texts(description="Illustrated with AI.\n" + DESC_EN), "en"))
        self.assertTrue(self.up.validate(texts(description="Dieses Video wurde mit KI erstellt.\nQuellen: A"), "de"))
        self.assertTrue(self.up.validate(texts(description="AIで生成した映像です。\n出典: A"), "ja"))
        self.assertTrue(self.up.validate(texts(description="Imágenes generadas con IA.\nFuentes: A"), "es"))
        self.assertTrue(self.up.validate(texts(title="x" * 101), "en"))
        self.assertTrue(self.up.validate(texts(tags=["t" * 300, "u" * 300]), "en"))
        self.assertTrue(self.up.validate({"title": 1}, "en"))

    def test_one_sources_line(self):
        self.assertTrue(self.up.validate(texts(description="No sources here."), "en"))
        self.assertTrue(self.up.validate(texts(description=DESC_EN + "\nSources: again"), "en"))
        self.assertEqual(self.up.validate(texts(description="Text.\nNguồn: Toàn thư"), "vi"), [])
        self.assertTrue(self.up.validate(texts(description="Text.\nSources: Toàn thư"), "vi"))  # wrong language prefix

    def test_chapters_from_timing(self):
        self.assertEqual(self.up.chapters(self.pdir, "vi"), "")  # no timing yet
        self.script.save(self.pdir, doc("vi"), "owner")
        os.makedirs(os.path.join(self.pdir, "lang", "vi"), exist_ok=True)
        timing = {"lang": "vi", "duration": 4000.0, "parts": [], "beats": [
            {"id": "B01", "start": 0.4, "end": 70, "sentences": []},
            {"id": "B02", "start": 75.2, "end": 600, "sentences": []},
            {"id": "B03", "start": 3725.0, "end": 4000, "sentences": []}]}
        json.dump(timing, open(os.path.join(self.pdir, "lang", "vi", "timing.json"), "w"))
        self.assertEqual(self.up.chapters(self.pdir, "vi"), "0:00 The hook\n1:15 The stakes\n1:02:05 The battle")

    def test_write_upload_md(self):
        self.up.write(self.pdir, "vi", texts(description="Mô tả.\nNguồn: Toàn thư"))
        md = open(os.path.join(self.pdir, "lang", "vi", "upload", "upload.md"), encoding="utf-8").read()
        self.assertIn("How Vietnam Beat the Mongol Fleet", md)
        self.assertIn("Nguồn: Toàn thư", md)
        self.assertIn("history, vietnam, mongols", md)
        self.assertIn("Khi upload: đặt nội dung thay đổi/tổng hợp = Có", md)
        self.assertNotIn("minh họa bằng AI", md)
        self.assertEqual(json.load(open(os.path.join(self.pdir, "lang", "vi", "upload", "upload.json")))["title"],
                         "How Vietnam Beat the Mongol Fleet")

    def test_job_writes_after_validation(self):
        self.seed_bank(claim("S1", "quân Nguyên đến sông Bạch Đằng", source_title="Đại Việt sử ký toàn thư"))
        self.fb.set_status(self.pdir, "F001", "verified", "claude", "", "A")
        with self.assertRaises(ValueError):
            self.jobs.enqueue("agy_upload_texts", {"project": "001-a", "lang": "vi"}, "001-a", "x")  # not approved
        self.script.save(self.pdir, doc("vi"), "owner")
        self.script.approve(self.pdir, "owner")
        self.fixture({"result.json": texts(description="Mô tả.\nNguồn: Đại Việt sử ký toàn thư")})
        j = self.jobs.enqueue("agy_upload_texts", {"project": "001-a", "lang": "vi"}, "001-a", "agy viết text upload VI")
        self.assertEqual(j["argv"][0], self.agy.AGY)
        run = j["params"]["run"]
        names = json.load(open(os.path.join(run, "sources.json"), encoding="utf-8"))
        self.assertIn("Đại Việt sử ký toàn thư", json.dumps(names, ensure_ascii=False))
        self.assertNotIn("http", json.dumps(names))
        self.assertTrue(os.path.isfile(os.path.join(run, "UPLOAD.md")))
        self.assertEqual(self.run_job(j), "done")
        self.assertTrue(os.path.isfile(os.path.join(self.pdir, "lang", "vi", "upload", "upload.md")))
        steps = {s["id"]: s["state"] for s in self.progress.get(self.pdir)["steps"]}
        self.assertEqual(steps["upload"], "wait")
        # a result with a link is refused whole
        self.fixture({"result.json": texts(description="Mô tả https://x.org\nNguồn: A", title="Khác")})
        j = self.jobs.enqueue("agy_upload_texts", {"project": "001-a", "lang": "vi"}, "001-a", "lại")
        self.run_job(j)
        self.assertEqual(json.load(open(os.path.join(self.pdir, "lang", "vi", "upload", "upload.json")))["title"],
                         "How Vietnam Beat the Mongol Fleet")
        self.assertTrue(any(i["kind"] == "job_failed" and "http" in i["text"] for i in self.inbox.open_items()))
