#!/usr/bin/env python3
"""usage: ziddi_chase.py [--dry-run | --live] [--config F] [--now "YYYY-MM-DD HH:MM"] [--user-active-at "YYYY-MM-DD HH:MM"] [--md FILE] [--json FILE] [flush]

The CHASE half of ziddi-af. Reads your signal sources (config "signals"), triages every candidate into CHASE NOW / BATCH / HOLD / DROP
with the reason, and prints them. DRY RUN is the default: nothing is sent, nothing is written.

  ziddi_chase.py --config ziddi.config.json --dry-run --md out.md
  ziddi_chase.py --live            send CHASE NOW items through the delivery adapter (queues them during quiet hours), record them in the gate
  ziddi_chase.py flush [--live]    send queued chases once quiet hours end or the user is active
  --user-active-at T               tell the engine the user was active at T (otherwise it reads the configured activity adapter)
  --gate-state PATH                use a throwaway gate file (for demos and tests)
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ziddi_lib import config as cfgmod, engine  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", choices=["run", "flush"], default="run")
    ap.add_argument("--config"); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--live", action="store_true")
    ap.add_argument("--now"); ap.add_argument("--user-active-at"); ap.add_argument("--active-label", default="operator-supplied")
    ap.add_argument("--gate-state"); ap.add_argument("--md"); ap.add_argument("--json")
    a = ap.parse_args()
    if a.live and a.dry_run:
        sys.exit("choose --dry-run or --live, not both")
    cfg, base = cfgmod.load(a.config)
    if a.cmd == "flush":
        print(json.dumps(engine.flush(cfg, base, a.now, a.user_active_at, live=a.live), indent=1))
        return
    items, meta = engine.run(cfg, base, a.now, a.user_active_at, a.active_label, a.gate_state, live=a.live)
    md = engine.render_md(items, meta, base)
    if a.json:
        def ser(o):
            return o.isoformat() if hasattr(o, "isoformat") else str(o)
        Path(a.json).write_text(json.dumps({"schema_version": 1, "meta": meta, "items": items}, indent=1, default=ser))
    if a.md:
        Path(a.md).write_text(md + "\n")
        print(f"wrote {a.md}: " + json.dumps(meta["counts"]))
    else:
        print(md)


if __name__ == "__main__":
    main()
