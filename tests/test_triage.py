import unittest

from _helpers import load_example, temp_home
from ziddi_lib import engine
from ziddi_lib.triage import BATCH, CHASE, DROP, HOLD


class TriageTests(unittest.TestCase):
    def run_example(self, now="2026-03-10 05:10", active="2026-03-10 04:50"):
        temp_home()
        cfg, base = load_example()
        items, meta = engine.run(cfg, base, now_override=now, active_at=active)
        return {i["key"]: i for i in items}, meta

    def cls(self, items, key):
        return items[key]["triage"]["class"]

    def test_expected_classes(self):
        items, meta = self.run_example()
        want = {"renewal-harbor-pine": CHASE, "dentist-slot": CHASE, "owed:s1": CHASE, "northwind-invoice": BATCH, "tls-cert-staging": BATCH,
                "job:render-demo-video": BATCH, "job:nightly-backup-check": BATCH, "owed:s4": BATCH, "nda-lumen": HOLD, "newsletter-cleanup": HOLD,
                "old-wiki": DROP, "seo-pitch": DROP, "job:index-rebuild": DROP, "owed:s5": DROP, "cal:20260313:Team offsite": HOLD}
        for k, c in want.items():
            self.assertEqual(self.cls(items, k), c, f"{k}: {items[k]['triage']['reason']}")
        self.assertEqual(sum(meta["counts"].values()), meta["total"])

    def test_every_candidate_has_class_and_reason(self):
        items, _ = self.run_example()
        for i in items.values():
            self.assertTrue(i["triage"]["reason"])
            self.assertIn(i["triage"]["class"], (CHASE, BATCH, HOLD, DROP))

    def test_chase_carries_artifact_or_is_the_answer(self):
        items, _ = self.run_example()
        for i in items.values():
            if i["triage"]["class"] == CHASE:
                self.assertTrue(i["artifact"] or i["recommendation"] or i["owed_reply"], i["key"])
                if not i["owed_reply"]:
                    self.assertIsNotNone(i["message"])

    def test_messages_are_short_and_clean(self):
        from ziddi_lib import message
        items, _ = self.run_example()
        for i in items.values():
            if i.get("message"):
                words, probs = message.lint(i["message"])
                self.assertEqual(probs, [], f"{i['key']}: {probs}")
                self.assertLessEqual(words, 70)

    def test_quiet_hours_queue_when_user_inactive(self):
        items, meta = self.run_example(active=None)
        self.assertTrue(meta["quiet_hours_now"])
        self.assertFalse(meta["deliver_now"])
        self.assertEqual(items["renewal-harbor-pine"]["triage"]["delivery"], "queue to the batch")
        items, meta = self.run_example(active="2026-03-10 05:00")
        self.assertEqual(items["renewal-harbor-pine"]["triage"]["delivery"], "now")

    def test_daytime_needs_no_override(self):
        items, meta = self.run_example(now="2026-03-10 10:00", active=None)
        self.assertTrue(meta["deliver_now"])

    def test_already_told_but_new_step_still_chases(self):
        items, _ = self.run_example()
        p = items["renewal-harbor-pine"]["triage"]["parts"]
        self.assertIn("Harbor", p["user_knows"])
        self.assertTrue(p["new_next_step"].startswith("yes"))

    def test_dry_run_writes_nothing(self):
        home = temp_home()
        cfg, base = load_example()
        engine.run(cfg, base, now_override="2026-03-10 05:10", active_at="2026-03-10 04:50")
        self.assertEqual(list(home.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
