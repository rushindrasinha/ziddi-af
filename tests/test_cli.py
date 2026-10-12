"""A stranger's first five minutes: everything works from a clean clone with no config and no access to anything private."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _helpers import EXAMPLE_CONFIG, ROOT, SCRIPTS

PY = sys.executable


def run(args, **kw):
    env = dict(os.environ, ZIDDI_HOME=tempfile.mkdtemp(prefix="ziddi-cli-"))
    env.pop("ZIDDI_CONFIG", None)
    return subprocess.run([PY, *args], capture_output=True, text=True, env=env, **kw)


class CliTests(unittest.TestCase):
    def test_help_on_every_script(self):
        for s in ("attempts.py", "ziddi_giveup_check.py", "ziddi_chase.py"):
            r = run([str(SCRIPTS / s), "--help"])
            self.assertEqual(r.returncode, 0, s)
            self.assertIn("usage", r.stdout.lower(), s)

    def test_detector_cli_exit_codes(self):
        self.assertEqual(run([str(SCRIPTS / "ziddi_giveup_check.py"), "--text", "I can't log in, only you can."]).returncode, 1)
        self.assertEqual(run([str(SCRIPTS / "ziddi_giveup_check.py"), "--text", "Shipped, all green."]).returncode, 0)

    def test_hooks_observe_then_enforce(self):
        payload = json.dumps({"tool_input": {"message": "I cannot get in, blocked."}})
        env = dict(os.environ, ZIDDI_HOME=tempfile.mkdtemp())
        p = subprocess.run([PY, str(SCRIPTS / "ziddi_giveup_check.py"), "--hook-pretool"], input=payload, capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 0)  # observe
        self.assertTrue((Path(env["ZIDDI_HOME"]) / "giveup_observe.jsonl").exists())
        p = subprocess.run([PY, str(SCRIPTS / "ziddi_giveup_check.py"), "--hook-pretool", "--enforce"], input=payload, capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 2)
        env["ZIDDI_OFF"] = "1"
        p = subprocess.run([PY, str(SCRIPTS / "ziddi_giveup_check.py"), "--hook-pretool", "--enforce"], input=payload, capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 0)

    def test_chase_dry_run_on_bundled_example(self):
        out = tempfile.mkdtemp() + "/out.md"
        r = run([str(SCRIPTS / "ziddi_chase.py"), "--config", str(EXAMPLE_CONFIG), "--dry-run", "--now", "2026-03-10 05:10", "--user-active-at", "2026-03-10 04:50", "--md", out])
        self.assertEqual(r.returncode, 0, r.stderr)
        text = Path(out).read_text()
        self.assertIn("CHASE NOW", text)
        self.assertIn("Harbor & Pine renewal quote", text)

    def test_shipped_example_matches_a_fresh_run(self):
        out = tempfile.mkdtemp() + "/out.md"
        run([str(SCRIPTS / "ziddi_chase.py"), "--config", str(EXAMPLE_CONFIG), "--dry-run", "--now", "2026-03-10 05:10", "--user-active-at", "2026-03-10 04:50", "--md", out])
        shipped = (ROOT / "examples" / "dry_run_example.md").read_text()
        self.assertEqual(Path(out).read_text().strip(), shipped.strip(), "examples/dry_run_example.md is stale: regenerate it (see examples/README.md)")


if __name__ == "__main__":
    unittest.main()
