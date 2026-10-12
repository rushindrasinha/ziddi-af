"""Escalation cadence: 1st touch carries the artifact; an unchanged item never repeats; the 2nd touch needs new information and
announces a reversible default; the 3rd touch executes that default instead of repeating louder. A gated item never gets a default."""
import copy
import unittest

from _helpers import load_example, temp_home
from ziddi_lib import engine
from ziddi_lib.triage import BATCH, CHASE, HOLD


class CadenceTests(unittest.TestCase):
    def setUp(self):
        self.home = temp_home()
        cfg, self.base = load_example()
        self.cfg = copy.deepcopy(cfg)
        self.cfg["delivery"] = {"adapter": "file", "path": str(self.home / "outbox.jsonl")}

    def go(self, now, active="2026-03-10 04:50"):
        items, meta = engine.run(self.cfg, self.base, now_override=now, active_at=active, live=True)
        return {i["key"]: i for i in items}, meta

    def test_three_touches(self):
        a, meta = self.go("2026-03-10 05:10")                    # touch 1
        self.assertEqual(a["dentist-slot"]["triage"]["class"], CHASE)
        self.assertIn("dentist-slot", meta["sent"])
        self.assertTrue((self.home / "outbox.jsonl").exists())
        b, _ = self.go("2026-03-10 05:40", active="2026-03-10 05:30")   # nothing new: held
        self.assertEqual(b["dentist-slot"]["triage"]["class"], HOLD)
        self.assertIn("identical info already sent", b["dentist-slot"]["triage"]["reason"])
        c, meta = self.go("2026-03-10 19:10", active="2026-03-10 19:00")  # inside the last hour: tier changed, 2nd touch with a default announced
        self.assertEqual(c["dentist-slot"]["triage"]["class"], CHASE)
        self.assertIn("I will book the 09:00 slot", c["dentist-slot"]["message"])
        d, _ = self.go("2026-03-10 20:30", active="2026-03-10 20:20")    # deadline passed, 2 touches done: execute the reversible default
        self.assertEqual(d["dentist-slot"]["triage"]["class"], BATCH)
        self.assertIn("EXECUTE DEFAULT", d["dentist-slot"]["triage"]["action"])

    def test_gated_item_never_gets_a_default(self):
        items = [{"id": "gated-wire", "title": "Approve the wire", "state": "Needs your approval.", "deadline": "2026-03-10 20:00", "money": 3, "waiting_on_user": True,
                  "recommendation": "approve", "steps": ["Say 'approve'"], "default_action": {"action": "send the wire", "reversible": True}}]
        tmp = self.home / "gated.json"
        import json
        tmp.write_text(json.dumps(items))
        self.cfg["signals"] = [{"adapter": "items", "path": str(tmp)}]
        a, _ = self.go("2026-03-10 05:10")
        self.assertEqual(a["gated-wire"]["triage"]["class"], CHASE)
        self.assertIsNone(a["gated-wire"]["default_note"])        # silence is never consent for a gated action
        self.go("2026-03-10 19:10", active="2026-03-10 19:00")
        c, _ = self.go("2026-03-10 20:30", active="2026-03-10 20:20")
        self.assertEqual(c["gated-wire"]["triage"]["class"], HOLD)  # no default, so no louder repeat either

    def test_queue_then_flush(self):
        _, meta = self.go("2026-03-10 05:10", active=None)       # quiet hours, user inactive: queued, not sent
        self.assertTrue(meta["queued"])
        self.assertFalse((self.home / "outbox.jsonl").exists())
        res = engine.flush(self.cfg, self.base, "2026-03-10 05:30", None, live=True)
        self.assertEqual(res["sent"], [])
        res = engine.flush(self.cfg, self.base, "2026-03-10 06:05", None, live=True)
        self.assertTrue(res["sent"])
        self.assertTrue((self.home / "outbox.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
