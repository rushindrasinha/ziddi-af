import json
import os
import subprocess
import sys
import unittest

from _helpers import SCRIPTS, temp_home
from ziddi_lib import detector

A = str(SCRIPTS / "attempts.py")


def run(*args, home):
    env = dict(os.environ, ZIDDI_HOME=str(home))
    return subprocess.run([sys.executable, A, *args], capture_output=True, text=True, env=env)


class AttemptsTests(unittest.TestCase):
    def test_ladder_refuses_then_allows(self):
        home = temp_home()
        r = run("add", "--goal", "open the report", "--rung", "tool", "--did", "first try", "--result", "fail", "--why", "login wall", "--cmd", "curl -A x https://a", home=home)
        zid = r.stdout.strip().splitlines()[0]
        self.assertRegex(zid, r"^zid-\d{8}-[0-9a-f]{4}$")
        # same binary with different flags is NOT a new mechanism
        r = run("add", "--id", zid, "--rung", "path", "--did", "second try", "--result", "fail", "--why", "same wall", "--cmd", "curl -L -H y https://b", home=home)
        self.assertIn("will not count as a new mechanism", r.stderr)
        r = run("verdict", zid, "--outcome", "exhausted", "--ask", "x", "--recommend", "y", home=home)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("rung 'assets' never tried", r.stderr)
        for rung, did, cmd in [("assets", "grep local scripts", "grep -r report ."), ("memory", "search notes", "notes search report"), ("web", "read the docs", "lynx docs")]:
            run("add", "--id", zid, "--rung", rung, "--did", did, "--result", "fail", "--why", "nothing useful", "--cmd", cmd, home=home)
        r = run("verdict", zid, "--outcome", "exhausted", "--ask", "paste the text", "--recommend", "send it", home=home)
        self.assertEqual(r.returncode, 0, r.stderr)
        path = home / "attempts.jsonl"
        self.assertEqual(detector.decide(f"I can't open it. {zid}", path, verify=True)["verdict"], "ok")
        r = run("receipt", zid, home=home)
        self.assertIn("I recommend: send it", r.stdout)

    def test_gated_needs_gate_and_budget_needs_time(self):
        home = temp_home()
        zid = run("add", "--goal", "g", "--rung", "tool", "--did", "d", "--result", "fail", "--why", "approval needed", home=home).stdout.strip()
        self.assertNotEqual(run("verdict", zid, "--outcome", "gated", home=home).returncode, 0)
        self.assertEqual(run("verdict", zid, "--outcome", "gated", "--gate", "approval", home=home).returncode, 0)
        zid2 = run("add", "--goal", "g2", "--rung", "tool", "--did", "d", "--result", "fail", "--why", "slow thing here", home=home).stdout.strip()
        self.assertNotEqual(run("verdict", zid2, "--outcome", "budget-stop", "--ask", "a", "--recommend", "b", home=home).returncode, 0)
        run("add", "--id", zid2, "--rung", "web", "--did", "d2", "--result", "fail", "--why", "slow thing here", "--cost-s", "1500", home=home)
        self.assertEqual(run("verdict", zid2, "--outcome", "budget-stop", "--ask", "a", "--recommend", "b", home=home).returncode, 0)

    def test_why_is_required(self):
        home = temp_home()
        r = run("add", "--goal", "g", "--rung", "tool", "--did", "d", "--result", "fail", "--why", "no", home=home)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
