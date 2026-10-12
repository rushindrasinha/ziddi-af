#!/usr/bin/env python3
"""usage: ziddi_giveup_check.py [--text T | --file F | stdin] [--verify] [--json] | --hook-stop | --hook-pretool [--enforce]

Flag a draft reply that gives up without an attempt-log id. Deterministic, stdlib, no model.

  ziddi_giveup_check.py --text "I can't open that page, only you can log in."     -> FLAG, exit 1
  ziddi_giveup_check.py --text "..." --verify                                     also checks the cited id's verdict
  ziddi_giveup_check.py --hook-stop                                               Claude Code Stop hook (reads hook JSON on stdin)
  ziddi_giveup_check.py --hook-pretool                                            PreToolUse hook for a message-sending tool (checks tool_input.message/text/caption)

Hook modes OBSERVE by default: they log to $ZIDDI_HOME/giveup_observe.jsonl and exit 0. Add --enforce to exit 2 with the reason on
stderr (blocks the stop or the send). Set ZIDDI_OFF=1 in sessions that write status digests. A bug here never breaks the host.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ziddi_lib import config as cfgmod, detector, store  # noqa: E402


def last_assistant_text(payload):
    if isinstance(payload.get("last_assistant_message"), str):
        return payload["last_assistant_message"]
    tp = payload.get("transcript_path")
    if not tp or not os.path.exists(tp):
        return ""
    last = ""
    for ln in open(tp, errors="replace"):
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        msg = r.get("message") if isinstance(r.get("message"), dict) else r
        if msg.get("role") != "assistant":
            continue
        c = msg.get("content")
        if isinstance(c, str):
            last = c
        elif isinstance(c, list):
            t = "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
            if t.strip():
                last = t
    return last


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text"); ap.add_argument("--file"); ap.add_argument("--verify", action="store_true")
    ap.add_argument("--hook-stop", action="store_true"); ap.add_argument("--hook-pretool", action="store_true")
    ap.add_argument("--enforce", action="store_true"); ap.add_argument("--json", action="store_true"); ap.add_argument("--config")
    a = ap.parse_args()
    cfg, _ = cfgmod.load(a.config)
    path = store.log_path(cfg)

    if a.hook_stop or a.hook_pretool:
        if os.environ.get("ZIDDI_OFF") == "1":
            return 0
        try:
            payload = json.loads(sys.stdin.read() or "{}")
            if a.hook_stop and payload.get("stop_hook_active"):
                return 0
            if a.hook_pretool:
                ti = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
                draft = next((ti[k] for k in ("message", "text", "caption") if isinstance(ti.get(k), str) and ti[k].strip()), "")
            else:
                draft = last_assistant_text(payload)
            res = detector.decide(draft, path, verify=True)
            if res["verdict"] == "flag":
                log = cfgmod.state_dir(cfg) / "giveup_observe.jsonl"
                log.parent.mkdir(parents=True, exist_ok=True)
                with open(log, "a") as f:
                    f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "mode": "enforce" if a.enforce else "observe",
                                        "hits": [h["match"] for h in res["hits"]], "reason": res["reason"]}) + "\n")
                if a.enforce:
                    sys.stderr.write("ziddi-af: this reply gives up without an attempt log. Climb the ladder (SKILL.md), log attempts with attempts.py, "
                                     f"then reply with the zid id. Reason: {res['reason']}. Hits: {', '.join(h['match'] for h in res['hits'][:4])}\n")
                    return 2
        except Exception:
            pass
        return 0

    text = a.text if a.text is not None else (Path(a.file).read_text() if a.file else sys.stdin.read())
    res = detector.decide(text, path, verify=a.verify)
    if a.json:
        print(json.dumps(res, indent=1))
    else:
        print(f"{res['verdict'].upper()}: {res['reason']}")
        for h in res["hits"]:
            print(f"  [{h['class']}] {h['match']!r}  <- {h['sentence'][:120]}")
    return 1 if res["verdict"] == "flag" else 0


if __name__ == "__main__":
    sys.exit(main())
