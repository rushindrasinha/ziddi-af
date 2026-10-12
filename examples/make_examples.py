#!/usr/bin/env python3
"""usage: make_examples.py   regenerate examples/dry_run_example.md, attempt_log_example.md and cadence_example.md from the real tools.
Everything here is invented: the people, companies and amounts are fictional."""
import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "skill" / "ziddi-af" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from ziddi_lib import config as cfgmod, engine  # noqa: E402

PY = sys.executable


def sh(args, env):
    r = subprocess.run([PY, *args], capture_output=True, text=True, env=env)
    return (r.stdout + r.stderr).strip(), r.returncode


def attempt_log():
    home = tempfile.mkdtemp(prefix="ziddi-demo-")
    A = str(SCRIPTS / "attempts.py")
    steps = [
        ("2026-03-10 09:31", ["add", "--goal", "Download the March statement from the vendor portal", "--rung", "tool", "--did", "Fetch the statement URL with curl", "--result", "fail",
                              "--why", "redirects to a login page", "--cmd", "curl -L https://portal.example.invalid/statements/2026-03.pdf"]),
        ("2026-03-10 09:33", ["add", "--id", "ID", "--rung", "fix-cause", "--did", "Retry with the session cookie from the saved profile", "--result", "fail",
                              "--why", "cookie expired on the 7th", "--cmd", "curl -L -b cookies.txt https://portal.example.invalid/statements/2026-03.pdf"]),
        ("2026-03-10 09:36", ["add", "--id", "ID", "--rung", "assets", "--did", "Look for an existing script or connector for this vendor", "--result", "partial",
                              "--why", "found vendor_export.py in my tools folder; it needs an API key that is not set", "--cmd", "grep -rl vendor ~/tools"]),
        ("2026-03-10 09:39", ["add", "--id", "ID", "--rung", "memory", "--did", "Search past notes for a way this worked before", "--result", "partial",
                              "--why", "February notes say the portal also emails the statement to the finance inbox", "--cmd", "notes search statement"]),
        ("2026-03-10 09:44", ["add", "--id", "ID", "--rung", "path", "--did", "Open the finance inbox export and look for the March email", "--result", "ok",
                              "--why", "found it; the PDF is attached to the 3rd's email", "--cmd", "python3 mail_export.py --folder finance"]),
    ]
    env = dict(os.environ, ZIDDI_HOME=home, ZIDDI_ATTEMPTS=str(Path(home) / "attempts.jsonl"))
    out, zid = [], None
    for now, args in steps:
        env["ZIDDI_NOW"] = now
        a = [x if x != "ID" else zid for x in args]
        text, rc = sh([str(SCRIPTS / "attempts.py"), *a], env)
        if zid is None:
            zid = text.splitlines()[0]
        out.append(f"$ ZIDDI_NOW='{now}' attempts.py {' '.join(repr(x) if ' ' in x else x for x in args).replace('ID', zid)}\n{zid if args[0] == 'add' and args[1] != '--id' else text.splitlines()[0]}")
    env["ZIDDI_NOW"] = "2026-03-10 09:45"
    text, _ = sh([A, "verdict", zid, "--outcome", "solved"], env)
    shown, _ = sh([A, "show", zid], env)
    # a second, failing goal: the ladder refuses to let the agent give up early
    env["ZIDDI_NOW"] = "2026-03-10 10:05"
    z2, _ = sh([A, "add", "--goal", "Pull the order list from the shop admin", "--rung", "tool", "--did", "Call the admin API", "--result", "fail", "--why", "401 with the stored token", "--cmd", "curl https://shop.example.invalid/api/orders"], env)
    z2 = z2.splitlines()[0]
    refuse, rc = sh([A, "verdict", z2, "--outcome", "exhausted", "--ask", "a fresh token", "--recommend", "create one"], env)
    for rung, did, cmd, why in [("path", "Try the CSV export endpoint", "wget https://shop.example.invalid/export.csv", "same 401, the export needs the same token"),
                               ("assets", "Check the credentials folder and the secrets manager for a newer token", "creds list --service shop", "only the expired token exists"),
                               ("memory", "Search past notes for how the token was refreshed", "notes search shop token", "refresh needs the owner to approve a login prompt on their phone"),
                               ("web", "Read the vendor docs for service tokens", "lynx docs.example.invalid/tokens", "service tokens exist but only an owner can create one")]:
        env["ZIDDI_NOW"] = "2026-03-10 10:12"
        sh([A, "add", "--id", z2, "--rung", rung, "--did", did, "--result", "fail", "--why", why, "--cmd", cmd], env)
    ok, _ = sh([A, "verdict", z2, "--outcome", "exhausted", "--ask", "Create a service token in the shop admin (2 minutes, only the owner can)", "--recommend", "Create it with read-only orders scope, then I pull the list and schedule a weekly refresh"], env)
    receipt, _ = sh([A, "receipt", z2], env)
    check_flag, _ = sh([str(SCRIPTS / "ziddi_giveup_check.py"), "--text", "I can't get the order list, only you can create a token."], env)
    check_ok, _ = sh([str(SCRIPTS / "ziddi_giveup_check.py"), "--verify", "--text", f"I can't get the order list without a service token, only you can create one. {z2}"], env)
    md = ["# A relentless attempt log (fictional)", "",
          "Two goals, both invented. The first is solved on the fifth attempt after two dead ends; the second shows the ladder refusing to let the agent give up early, then letting it once the rungs are covered.", "",
          "## Goal 1: solved", "", "```text", "\n\n".join(out), "", "$ attempts.py verdict " + zid + " --outcome solved", text, "", "$ attempts.py show " + zid, shown, "```", "",
          "## Goal 2: the ladder says no, then yes", "", "```text", "$ attempts.py verdict " + z2 + " --outcome exhausted --ask ... --recommend ...", refuse, "",
          "(four more attempts: path, assets, memory, web)", "", "$ attempts.py verdict " + z2 + " --outcome exhausted --ask ... --recommend ...", ok, "",
          "$ attempts.py receipt " + z2, receipt, "", "$ ziddi_giveup_check.py --text \"I can't get the order list, only you can create a token.\"", check_flag, "",
          "$ ziddi_giveup_check.py --verify --text \"... " + z2 + "\"", check_ok, "```", ""]
    (HERE / "attempt_log_example.md").write_text("\n".join(md))


def cadence():
    os.environ["ZIDDI_HOME"] = tempfile.mkdtemp(prefix="ziddi-cad-")
    home = Path(os.environ["ZIDDI_HOME"])
    cfg, base = cfgmod.load(str(HERE / "ziddi.example.config.json"))
    cfg = copy.deepcopy(cfg)
    cfg["delivery"] = {"adapter": "file", "path": str(home / "outbox.jsonl")}
    runs = [("2026-03-10 05:10", "2026-03-10 04:50", "Quiet hours, but the user messaged 20 minutes ago, so a chase goes out. Touch 1."),
            ("2026-03-10 05:40", "2026-03-10 05:30", "30 minutes later, nothing new. Held."),
            ("2026-03-10 19:10", "2026-03-10 19:00", "Under an hour to the deadline: new information. Touch 2 announces the pre-agreed default."),
            ("2026-03-10 20:30", "2026-03-10 20:20", "Deadline passed after two touches. Touch 3 is not a louder repeat: the reversible default is carried out and reported.")]
    rows = ["| Run at | What the engine did with `dentist-slot` | Why |", "|---|---|---|"]
    blocks = []
    for now, active, why in runs:
        items, meta = engine.run(cfg, base, now_override=now, active_at=active, live=True)
        i = next(x for x in items if x["key"] == "dentist-slot")
        t = i["triage"]
        what = t["class"] + (f": {t['action']}" if t.get("action") else "")
        rows.append(f"| {now} | {what} | {why} |")
        if i.get("message") and "dentist-slot" in meta.get("sent", []):
            blocks.append(f"Message sent at {now}:\n\n```text\n{i['message']}\n```\n")
    md = ["# The escalation cadence, on a fictional item", "",
          "Item: pick a dentist slot before the clinic releases it at 20:00. Pre-agreed default: book the 09:00 slot tomorrow (free to cancel until 18:00 tomorrow). Same engine, four runs, delivery by the `file` adapter in a temporary folder.", "",
          *rows, "", *blocks, "A gated item (`waiting_on_user`) never gets a default: with no default, the third touch is held instead of repeated. Silence is not consent.", ""]
    (HERE / "cadence_example.md").write_text("\n".join(md))


def dry_run():
    env = dict(os.environ, ZIDDI_HOME=tempfile.mkdtemp())
    sh([str(SCRIPTS / "ziddi_chase.py"), "--config", str(HERE / "ziddi.example.config.json"), "--dry-run", "--now", "2026-03-10 05:10", "--user-active-at", "2026-03-10 04:50",
        "--md", str(HERE / "dry_run_example.md")], env)


if __name__ == "__main__":
    dry_run()
    attempt_log()
    cadence()
    print("examples regenerated")
