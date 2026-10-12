import unittest

from _helpers import ROOT, temp_home
from ziddi_lib import detector


class DetectorTests(unittest.TestCase):
    def test_flags_plain_giveups(self):
        for t in ["I can't open the dashboard.", "I'm blocked on the API key, only you can create one.", "The upload still doesn't work after two tries.",
                  "There is no way to do this through the public API.", "This step needs you to log in with your own account."]:
            self.assertTrue(detector.find_giveups(t), t)

    def test_does_not_flag_gates_recoveries_quotes_negations(self):
        for t in ["Need your approval before I publish this post.", "Fixed it. The upload didn't work at first, so I switched to the CLI and it passes now.",
                  '"I cannot access external URLs" was printed in the log.', "Not blocked on anything right now.", "If that doesn't work, fall back to the manual export.",
                  "I can't tell which file is newer from the screenshot.", "Status digest: nothing waiting on you.", "I won't send this without your sign-off."]:
            self.assertFalse(detector.find_giveups(t), t)

    def test_code_blocks_are_ignored(self):
        self.assertFalse(detector.find_giveups("Here is the log:\n```\nError: I cannot connect, blocked by firewall\n```\nAll fine now."))

    def test_attempt_id_required_and_verified(self):
        home = temp_home()
        res = detector.decide("I can't open the page.", home / "a.jsonl")
        self.assertEqual(res["verdict"], "flag")
        res = detector.decide("I can't open the page. See zid-20260310-abcd.", home / "a.jsonl", verify=False)
        self.assertEqual(res["verdict"], "ok")
        res = detector.decide("I can't open the page. See zid-20260310-abcd.", home / "a.jsonl", verify=True)
        self.assertEqual(res["verdict"], "flag")  # id not in the log

    def test_regression_set(self):
        tp = fp = fn = tn = 0
        lines = (ROOT / "skill/ziddi-af/references/giveup_testset.txt").read_text(encoding="utf-8").splitlines()
        for ln in lines:
            if ln[:2] not in ("P|", "N|"):
                continue
            flagged = bool(detector.find_giveups(ln[2:].strip()))
            if ln[0] == "P":
                tp, fn = tp + flagged, fn + (not flagged)
            else:
                fp, tn = fp + flagged, tn + (not flagged)
        precision, recall = tp / (tp + fp), tp / (tp + fn)
        self.assertGreaterEqual(precision, 0.85, f"precision {precision:.2f}")
        self.assertGreaterEqual(recall, 0.60, f"recall {recall:.2f}")


if __name__ == "__main__":
    unittest.main()
