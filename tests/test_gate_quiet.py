import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from _helpers import load_example
from ziddi_lib import config as cfgmod
from ziddi_lib.gate import Gate
from ziddi_lib.quiet import deliver_now, in_quiet_hours, is_active

UTC = timezone.utc


class GateTests(unittest.TestCase):
    def test_unchanged_never_repeats_changed_does(self):
        p = Path(tempfile.mkdtemp()) / "g.json"
        g = Gate(p, write=True)
        self.assertEqual(g.peek("k", "a")[0], True)
        g.record("k", "a")
        g2 = Gate(p)
        self.assertEqual(g2.peek("k", "a")[0], False)   # identical: held, however much time passes
        self.assertEqual(g2.peek("k", "b")[0], True)    # new info: allowed
        self.assertEqual(g2.touches("k"), 1)
        g2.write = True
        g2.record("k", "b")
        self.assertEqual(Gate(p).touches("k"), 2)

    def test_dry_run_gate_never_writes(self):
        p = Path(tempfile.mkdtemp()) / "g.json"
        g = Gate(p, write=False)
        g.record("k", "a")
        self.assertFalse(p.exists())


class QuietTests(unittest.TestCase):
    def setUp(self):
        self.cfg, _ = load_example()

    def at(self, hh, mm=0):
        return datetime(2026, 3, 10, hh, mm, tzinfo=UTC)

    def test_window(self):
        self.assertTrue(in_quiet_hours(self.at(0, 0), self.cfg))
        self.assertTrue(in_quiet_hours(self.at(5, 59), self.cfg))
        self.assertFalse(in_quiet_hours(self.at(6, 0), self.cfg))
        self.assertFalse(in_quiet_hours(self.at(23, 59), self.cfg))

    def test_wraparound_window(self):
        cfg = dict(self.cfg, quiet_hours={"enabled": True, "start": "22:00", "end": "07:00"})
        self.assertTrue(in_quiet_hours(self.at(23), cfg))
        self.assertTrue(in_quiet_hours(self.at(3), cfg))
        self.assertFalse(in_quiet_hours(self.at(12), cfg))

    def test_active_override(self):
        now = self.at(3, 0)
        self.assertFalse(deliver_now(now, None, self.cfg))                          # quiet and nobody around: queue
        self.assertTrue(deliver_now(now, now - timedelta(minutes=10), self.cfg))    # active 10 min ago: deliver
        self.assertFalse(deliver_now(now, now - timedelta(minutes=45), self.cfg))   # active 45 min ago: window is 30
        self.assertTrue(deliver_now(self.at(9), None, self.cfg))                    # daytime: deliver

    def test_tz_helpers(self):
        self.assertEqual(cfgmod.get_tz("+05:30").utcoffset(None), timedelta(hours=5, minutes=30))
        self.assertEqual(cfgmod.get_tz("UTC").utcoffset(None), timedelta(0))
        self.assertIsNone(cfgmod.parse_dt("not a date", UTC))


if __name__ == "__main__":
    unittest.main()
