import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

WS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

SOURCES = {"S1": {"id": "S1", "grade": "A", "kind": "primary_record"}, "S2": {"id": "S2", "grade": "B", "kind": "news"},
           "S3": {"id": "S3", "grade": "B", "kind": "news"}, "S4": {"id": "S4", "grade": "A", "kind": "archaeology"}}


def fact(fid, src, status="verified", **kw):
    f = {"id": fid, "claim": "", "quote": "", "source": src, "grade": SOURCES[src]["grade"], "status": status,
         "legend": False, "conflicts_with": [], "kind": SOURCES[src]["kind"]}
    f.update(kw)
    return f


FACTS = {f["id"]: f for f in [fact("F1", "S1", claim="400 chiến thuyền bị bắt", quote="bắt được 400 chiến thuyền"),
                              fact("F2", "S2", claim="400 chiến thuyền"), fact("F3", "S3", claim="có 400 chiếc"), fact("F4", "S2", "weak"),
                              fact("F5", "S1", "conflict"), fact("F6", "S1", "rejected"), fact("F7", "S1", legend=True),
                              fact("F8", "S4")]}


def s(text, facts=(), kind="narration"):
    return {"id": "s001", "text": text, "facts": list(facts), "kind": kind, "note": ""}


def sample_script():
    return {"lang": "vi", "chapters": [{"id": "C01", "title": "Mở đầu", "beats": [{"id": "B01", "goal": "hook", "sentences": [
        {"id": "s001", "text": "Bạn có biết chuyện này không?", "facts": [], "kind": "question", "note": ""},
        {"id": "s002", "text": "Rồi quân Nguyên đến sông Bạch Đằng.", "facts": ["F1"], "kind": "fact", "note": ""},
    ]}]}]}


class ScriptTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "config"))
        shutil.copy(os.path.join(WS, "config", "languages.json"), os.path.join(self.root, "config"))
        os.environ["LONGFORM_ROOT"] = self.root
        from tools.longform import inbox, project, script
        self.script, self.inbox = script, inbox
        self.p = mock.patch.object(inbox.notify, "send", lambda t: True)
        self.p.start()
        self.pdir = project.create_project(1, "a", "A", [])
        os.makedirs(os.path.join(self.pdir, "research"), exist_ok=True)
        json.dump(SOURCES, open(os.path.join(self.pdir, "research", "sources.json"), "w"))
        with open(os.path.join(self.pdir, "research", "facts.jsonl"), "w") as f:
            for x in FACTS.values():
                f.write(json.dumps(x) + "\n")

    def tearDown(self):
        self.p.stop()
        os.environ.pop("LONGFORM_ROOT", None)
        shutil.rmtree(self.root)

    def colour(self, sentence):
        return self.script.colour(sentence, SOURCES, FACTS)

    def test_is_factual(self):
        f = self.script.is_factual
        self.assertTrue(f(s("Ai cũng biết", kind="fact")))
        self.assertTrue(f(s("Có 400 chiếc thuyền.")))
        self.assertTrue(f(s("Rồi Trần Hưng Đạo nhìn ra sông.")))
        self.assertFalse(f(s("Bạn thử đoán xem?")))
        self.assertFalse(f(s("Nghe thì dễ, làm mới khó.")))
        self.assertFalse(f(s("Câu hỏi là: Tại sao vậy?")))

    def test_colour_green(self):
        self.assertEqual(self.colour(s("Rồi Trần Hưng Đạo nhìn ra sông.", ["F1"]))["colour"], "green")

    def test_colour_plain(self):
        self.assertEqual(self.colour(s("Nghe thì dễ, làm mới khó."))["colour"], "plain")

    def test_colour_red_no_fact(self):
        c = self.colour(s("Rồi Trần Hưng Đạo nhìn ra sông."))
        self.assertEqual(c["colour"], "red")
        self.assertTrue(c["reasons"])

    def test_colour_red_rejected_fact(self):
        self.assertEqual(self.colour(s("Rồi Trần Hưng Đạo nhìn ra sông.", ["F6"]))["colour"], "red")
        self.assertEqual(self.colour(s("Rồi Trần Hưng Đạo nhìn ra sông.", ["F99"]))["colour"], "red")

    def test_number_needs_a_or_two_b(self):
        self.assertEqual(self.colour(s("Có 400 chiếc thuyền.", ["F1"]))["colour"], "green")
        self.assertEqual(self.colour(s("Có 400 chiếc thuyền.", ["F2"]))["colour"], "red")
        self.assertEqual(self.colour(s("Có 400 chiếc thuyền.", ["F2", "F3"]))["colour"], "green")

    def test_number_words_are_numbers(self):
        self.assertTrue(self.script.is_factual(s("Ba mươi vạn quân tràn sang biên giới.")))
        self.assertTrue(self.script.is_factual(s("Quân giặc có năm trăm chiến thuyền.")))
        self.assertEqual(self.colour(s("Quân giặc có năm trăm chiến thuyền."))["colour"], "red")
        c = self.colour(s("Quân giặc có bốn trăm chiến thuyền.", ["F1"]))
        self.assertEqual(c["colour"], "yellow")  # cannot compare words with the fact: the owner checks
        self.assertEqual(self.colour(s("Quân giặc có bốn trăm chiến thuyền.", ["F2"]))["colour"], "red")  # one B

    def test_number_must_match_fact(self):
        self.assertEqual(self.colour(s("Có 999.999 chiếc thuyền.", ["F1"]))["colour"], "red")
        self.assertEqual(self.colour(s("Có 400 chiếc thuyền.", ["F1"]))["colour"], "green")
        self.assertEqual(self.colour(s("Năm 1288 có 400 chiếc thuyền.", ["F1"]))["colour"], "red")  # 1288 not in F1

    def test_unreviewed_sentence_yellow(self):
        x = s("Rồi Trần Hưng Đạo nhìn ra sông.", ["F1"])
        x["reviewed"] = False
        c = self.colour(x)
        self.assertEqual(c["colour"], "yellow")
        self.assertIn("chưa soát", " ".join(c["reasons"]))

    def test_approval_cleared_when_fact_turns_bad(self):
        from tools.longform import factbank
        self.script.save(self.pdir, sample_script(), "agy")
        self.script.approve(self.pdir, "owner")
        with open(os.path.join(self.pdir, "research", "facts.jsonl"), "w") as f:
            for x in FACTS.values():
                f.write(json.dumps(dict(x, status="rejected") if x["id"] == "F1" else x) + "\n")
        self.assertTrue(self.script.recheck_approval(self.pdir))
        self.assertFalse(self.script.load(self.pdir)["approved"])
        self.assertEqual([i["kind"] for i in self.inbox.open_items()], ["script_approve"])

    def test_approve_refused_while_review_runs(self):
        from tools.longform import jobs
        self.script.save(self.pdir, sample_script(), "agy")
        kinds = dict(jobs.KINDS)
        try:
            jobs.register(jobs.Kind("claude_review", "claude", lambda p: ["true"]))
            jobs.enqueue("claude_review", {"project": "001-a"}, "001-a", "review")
            with self.assertRaisesRegex(ValueError, "Claude đang soát"):
                self.script.approve(self.pdir, "owner")
        finally:
            jobs.KINDS.clear()
            jobs.KINDS.update(kinds)

    def test_save_refuses_stale_base(self):
        self.script.save(self.pdir, sample_script(), "agy")
        d = self.script.load(self.pdir)
        self.script.save(self.pdir, d, "owner")  # v2
        with self.assertRaisesRegex(ValueError, "đã đổi"):
            self.script.save(self.pdir, d, "claude", base=1)
        self.assertEqual(self.script.load(self.pdir)["version"], 2)

    def test_update_is_locked_read_modify_write(self):
        import threading
        self.script.save(self.pdir, sample_script(), "agy")

        def bump(data):
            data["chapters"][0]["title"] += "x"
            return data
        ts = [threading.Thread(target=self.script.update, args=(self.pdir, bump, "t")) for _ in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        d = self.script.load(self.pdir)
        self.assertEqual((d["version"], d["chapters"][0]["title"]), (9, "Mở đầu" + "x" * 8))

    def test_yellow_conflict(self):
        self.assertEqual(self.colour(s("Rồi Ô Mã Nhi bị bắt.", ["F5"]))["colour"], "yellow")
        self.assertEqual(self.colour(s("Rồi Ô Mã Nhi bị bắt.", ["F1", "F4"]))["colour"], "yellow")

    def test_legend_needs_tuong_truyen(self):
        self.assertEqual(self.colour(s("Ông bẻ gậy thề trước Hưng Đạo Vương.", ["F7"]))["colour"], "red")
        self.assertEqual(self.colour(s("Tương truyền ông bẻ gậy thề trước Hưng Đạo Vương.", ["F7"]))["colour"], "green")

    def test_chung_minh_red(self):
        self.assertEqual(self.colour(s("Bãi cọc ở Yên Giang chứng minh điều đó.", ["F8"]))["colour"], "red")
        self.assertEqual(self.colour(s("Bãi cọc ở Yên Giang cho thấy điều đó.", ["F8"]))["colour"], "green")

    def test_banned_words_red(self):
        self.assertEqual(self.colour(s("Rồi chúng ta cùng xem."))["colour"], "red")
        self.assertEqual(self.colour(s("Này bạn nhỏ, nghe nhé."))["colour"], "red")

    def test_save_versions(self):
        self.assertIsNone(self.script.load(self.pdir))
        self.assertEqual(self.script.save(self.pdir, sample_script(), "agy"), 1)
        d = self.script.load(self.pdir)
        d["chapters"][0]["title"] = "Mở màn"
        self.assertEqual(self.script.save(self.pdir, d, "owner"), 2)
        self.assertTrue(os.path.isfile(os.path.join(self.pdir, "script", "versions", "v001.json")))
        self.assertEqual(self.script.load(self.pdir)["version"], 2)
        from tools.longform import progress
        self.assertEqual(progress.get(self.pdir)["steps"][1]["state"], "doing")

    def test_edit_clears_approval(self):
        self.script.save(self.pdir, sample_script(), "agy")
        self.script.approve(self.pdir, "owner")
        d = self.script.load(self.pdir)
        d["chapters"][0]["title"] = "Đổi tên chương"  # title only: approval stays
        self.script.save(self.pdir, d, "owner")
        self.assertTrue(self.script.load(self.pdir)["approved"])
        d = self.script.load(self.pdir)
        d["chapters"][0]["beats"][0]["sentences"][0]["text"] = "Bạn đoán thử xem?"
        self.script.save(self.pdir, d, "owner")
        self.assertFalse(self.script.load(self.pdir)["approved"])
        from tools.longform import progress
        self.assertEqual(progress.get(self.pdir)["steps"][1]["state"], "doing")

    def test_report(self):
        self.script.save(self.pdir, sample_script(), "agy")
        r = self.script.report(self.pdir)
        self.assertEqual((r["red"], r["yellow"], r["green"]), (0, 0, 1))
        self.assertEqual(r["sentences"][1], {"id": "s002", "beat": "B01", "colour": "green", "reasons": []})

    def test_approve_refused_with_red(self):
        d = sample_script()
        d["chapters"][0]["beats"][0]["sentences"].append(
            {"id": "s003", "text": "Có 500.000 quân.", "facts": [], "kind": "fact", "note": ""})
        self.script.save(self.pdir, d, "agy")
        with self.assertRaisesRegex(ValueError, "còn 1 câu đỏ"):
            self.script.approve(self.pdir, "owner")
        self.assertFalse(self.script.load(self.pdir)["approved"])

    def test_approve_sets_step_done(self):
        self.script.save(self.pdir, sample_script(), "agy")
        self.inbox.add("001-a", "script_approve", "chờ chốt", key="script:001-a")
        self.script.approve(self.pdir, "owner")
        from tools.longform import progress
        self.assertEqual(progress.get(self.pdir)["steps"][1]["state"], "done")
        self.assertEqual(self.inbox.open_items(), [])


if __name__ == "__main__":
    unittest.main()
