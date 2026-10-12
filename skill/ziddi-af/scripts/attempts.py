#!/usr/bin/env python3
"""usage: attempts.py {add|show|verdict|receipt|open} [options]

The ziddi-af attempt log. A reply that gives up must cite one of these ids. Log: $ZIDDI_HOME/attempts.jsonl (default ~/.ziddi/attempts.jsonl),
append-only, one JSON row per line.

  attempts.py add --goal "what the user asked for" --rung tool --did "what you did" --result fail --why "why it failed" [--cmd "command"] [--mechanism key] [--id zid-...] [--cost-s N]
      The first add for a goal omits --id and prints a new id (zid-YYYYMMDD-xxxx). Later adds pass --id.
  attempts.py show <id>
  attempts.py verdict <id> --outcome solved|exhausted|gated|budget-stop --ask "the one thing needed from the user" --recommend "what you suggest" [--gate name] [--budget-min N]
  attempts.py receipt <id>        the escalation block to paste into the reply
  attempts.py open                ids with attempts and no verdict yet

Rungs (genuinely different mechanisms, not the same command with new flags):
  fix-cause  retry after fixing the diagnosed cause     tool     a different tool for the same job
  path       a different API / CLI / endpoint / route   assets   existing scripts, MCP servers, credentials in your own setup  (required)
  memory     notes, memory, past transcripts            web      web, docs, source
  decompose  solve the solvable sub-part                adjacent an adjacent outcome that gets most of the value

`exhausted` needs 4 distinct mechanisms over 3 rungs including `assets` and `memory`, each with a real --why (all configurable).
`gated` is for guardrails (approval, publish rule, production guardrail, data-loss gate): cite it with --gate; a gate is never routed around.
`budget-stop` needs elapsed time >= the budget (default 20 minutes).
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ziddi_lib import config as cfgmod, store  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config")
    sub = ap.add_subparsers(dest="c", required=True)
    p = sub.add_parser("add"); p.add_argument("--goal"); p.add_argument("--id"); p.add_argument("--rung", required=True)
    p.add_argument("--did", required=True); p.add_argument("--result", required=True, choices=["fail", "partial", "ok"])
    p.add_argument("--why", required=True); p.add_argument("--cmd"); p.add_argument("--mechanism"); p.add_argument("--cost-s", type=int, default=0)
    p = sub.add_parser("show"); p.add_argument("id")
    p = sub.add_parser("verdict"); p.add_argument("id"); p.add_argument("--outcome", required=True, choices=["solved", "exhausted", "gated", "budget-stop"])
    p.add_argument("--ask"); p.add_argument("--recommend"); p.add_argument("--gate"); p.add_argument("--budget-min", type=int)
    p = sub.add_parser("receipt"); p.add_argument("id")
    sub.add_parser("open")
    a = ap.parse_args()
    cfg, _ = cfgmod.load(a.config)
    path = store.log_path(cfg)
    tz = cfgmod.get_tz(cfg["timezone"])
    now = cfgmod.now_in(tz, os.environ.get('ZIDDI_NOW'))  # ZIDDI_NOW pins the clock for demos and tests
    rows = store.read_rows(path)

    if a.c == "add":
        if a.rung not in store.RUNGS:
            sys.exit(f"rung must be one of {store.RUNGS}")
        if len(a.why.strip()) < 8:
            sys.exit("--why is required: say why this attempt failed (or what it proved)")
        zid = a.id or store.new_id(a.goal or "", now)
        existing = store.attempts_for(rows, zid)
        goal = a.goal or (existing[0]["goal"] if existing else None)
        if not goal:
            sys.exit("--goal is required on the first attempt for an id")
        key = store.mechanism_key(a.rung, a.did, a.cmd, a.mechanism)
        dup = any(r["mechanism"] == key for r in existing)
        store.append(path, {"kind": "attempt", "id": zid, "ts": now.isoformat(timespec="seconds"), "goal": goal, "rung": a.rung, "mechanism": key,
                            "did": a.did, "cmd": a.cmd, "result": a.result, "why": a.why, "cost_s": a.cost_s})
        print(zid)
        if dup:
            print(f"note: mechanism {key!r} was already tried in this id; it will not count as a new mechanism", file=sys.stderr)
        if a.result == "ok":
            print(f"note: result=ok, so close with: attempts.py verdict {zid} --outcome solved", file=sys.stderr)
        return

    if a.c == "open":
        ids = {}
        for r in rows:
            ids.setdefault(r["id"], []).append(r)
        for zid, rs in ids.items():
            if not any(r["kind"] == "verdict" for r in rs):
                at = [r for r in rs if r["kind"] == "attempt"]
                print(f"{zid}  {len(at)} attempts  {at[0]['goal'][:70]}  (last {at[-1]['ts']})")
        return

    att = store.attempts_for(rows, a.id)
    if not att:
        sys.exit(f"{a.id}: no attempts logged")
    verdicts = [r for r in rows if r.get("id") == a.id and r.get("kind") == "verdict"]

    if a.c == "show":
        print(f"{a.id}  goal: {att[0]['goal']}")
        for i, r in enumerate(att, 1):
            print(f"  {i}. [{r['rung']}] {r['mechanism']}: {r['did']} -> {r['result']}. {r['why']}")
        solved = bool(verdicts) and verdicts[-1]["verdict"] == "solved"
        probs = [] if solved else store.ladder_problems(att, cfg)
        print(f"  mechanisms={len({r['mechanism'] for r in att})} rungs={len({r['rung'] for r in att})} elapsed={store.elapsed_minutes(att):.1f}min " + ("solved: no ladder needed" if solved else f"ladder_complete={not probs}"))
        for pr in probs:
            print(f"    missing: {pr}")
        if verdicts:
            v = verdicts[-1]
            print(f"  verdict: {v['verdict']}  ask: {v.get('ask')}  recommend: {v.get('recommend')}  gate: {v.get('gate')}")
    elif a.c == "verdict":
        if a.outcome == "solved" and not any(r["result"] == "ok" for r in att):
            sys.exit("solved needs at least one attempt with --result ok")
        if a.outcome == "exhausted":
            probs = store.ladder_problems(att, cfg)
            if probs:
                sys.exit("cannot call this exhausted yet:\n  - " + "\n  - ".join(probs) + "\nKeep climbing the ladder.")
            if not (a.ask and a.recommend):
                sys.exit("exhausted needs --ask (the one thing needed from the user) and --recommend")
        if a.outcome == "gated" and not a.gate:
            sys.exit("gated needs --gate <approval|publish-rule|production-guardrail|data-loss|refused-action|...>")
        if a.outcome == "budget-stop":
            budget = a.budget_min or cfg["attempts"]["budget_minutes"]
            if store.elapsed_minutes(att) < budget:
                sys.exit(f"budget-stop needs >= {budget} min spent; logged {store.elapsed_minutes(att):.1f} min. Keep going, or log real cost with --cost-s.")
            if not (a.ask and a.recommend):
                sys.exit("budget-stop needs --ask and --recommend")
        store.append(path, {"kind": "verdict", "id": a.id, "ts": now.isoformat(timespec="seconds"), "verdict": a.outcome, "ask": a.ask, "recommend": a.recommend,
                            "gate": a.gate, "mechanisms": len({r['mechanism'] for r in att}), "attempts": len(att), "elapsed_min": round(store.elapsed_minutes(att), 1)})
        print(f"{a.id} verdict={a.outcome} ({len(att)} attempts, {len({r['mechanism'] for r in att})} mechanisms)")
    elif a.c == "receipt":
        if not verdicts:
            sys.exit("needs a verdict first")
        v = verdicts[-1]
        print(f"Attempt log {a.id}: {len(att)} tries, {len({r['mechanism'] for r in att})} different mechanisms.")
        for r in att:
            print(f"- {r['did']} ({r['rung']}): {r['why']}")
        if v.get("gate"):
            print(f"Gate: {v['gate']} (not routed around).")
        print(f"I need from you: {v.get('ask')}")
        print(f"I recommend: {v.get('recommend')}")


if __name__ == "__main__":
    main()
