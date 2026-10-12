"""The chase engine: collect candidates, triage each one, render, and (only with --live) deliver.

Dry run is the default and the safe mode: nothing is sent, nothing is written. `--live` needs a real delivery adapter in config
(stdout counts) and records every delivery in the gate so the same thing is never said twice.
"""
import json
import os
from datetime import datetime
from pathlib import Path

from . import adapters, config as cfgmod, message
from .gate import Gate
from .quiet import deliver_now, in_quiet_hours, is_active
from .triage import BATCH, CHASE, DROP, HOLD, ORDER, classify


def run(cfg, base_dir, now_override=None, active_at=None, active_label="operator-supplied", gate_path=None, live=False, only_adapters=None):
    tz = cfgmod.get_tz(cfg["timezone"])
    now = cfgmod.now_in(tz, now_override)
    sd = cfgmod.state_dir(cfg)
    gate = Gate(gate_path or sd / "gate.json", write=live)
    known = [cfgmod.resolve_path(p, base_dir) for p in cfg.get("known_logs", [])] + [sd / "sent.jsonl"]
    know = adapters.Knowledge(known, tz)
    override = (cfgmod.parse_dt(active_at, tz), active_label) if active_at else None
    activity = adapters.last_user_activity(cfg, base_dir, tz, override)
    last = activity[0][0] if activity else None
    ctx_deliver = deliver_now(now, last, cfg)

    items, sources, jobs = [], [], []
    for spec in cfg.get("signals", []):
        if only_adapters and spec["adapter"] not in only_adapters:
            continue
        fn = adapters.SIGNALS.get(spec["adapter"])
        if not fn:
            sources.append({"name": spec["adapter"], "ok": False, "note": "unknown signal adapter", "n": 0})
            continue
        try:
            its, st = fn(spec, cfg, base_dir, tz, now)
        except Exception as e:  # one broken source never hides the others
            its, st = [], {"name": spec.get("name", spec["adapter"]), "ok": False, "note": f"{e.__class__.__name__}: {e}"}
        st["n"] = len(its)
        sources.append(st)
        items += its
        if spec["adapter"] == "jobs":
            jobs += [i["key"][4:] for i in its]

    ctx = {"now": now, "cfg": cfg, "gate": gate, "knowledge": know, "jobs": jobs, "deliver_now": ctx_deliver}
    for it in items:
        it["triage"] = classify(it, ctx)
        it["message"] = message.build_message(it) if (it["triage"]["class"] == CHASE and not it["owed_reply"]) else None
    items.sort(key=lambda i: (ORDER[i["triage"]["class"]], -i["triage"]["parts"]["importance"]))
    counts = {c: sum(1 for i in items if i["triage"]["class"] == c) for c in ORDER}
    meta = {"generated_at": now.strftime("%Y-%m-%d %H:%M %Z").strip(), "quiet_hours_now": in_quiet_hours(now, cfg), "user_active": is_active(now, last, cfg),
            "deliver_now": ctx_deliver, "activity": [{"at": f"{d:%Y-%m-%d %H:%M}", "surface": s} for d, s in activity[:4]],
            "counts": counts, "total": len(items), "sources": sources, "live": live}
    if live:
        _deliver_live(items, cfg, base_dir, gate, now, ctx_deliver, meta)
    return items, meta


def _queue_path(cfg):
    return cfgmod.state_dir(cfg) / "queue.json"


def _deliver_live(items, cfg, base_dir, gate, now, deliver_now_flag, meta):
    sent, queued = [], []
    q = []
    for it in items:
        if it["triage"]["class"] != CHASE or not it["message"]:
            continue
        if deliver_now_flag:
            ok, why = adapters.deliver(it["message"], cfg, base_dir, it["key"], dry=False)
            if ok:
                gate.record(it["key"], it["gate_tier"])
                adapters.record_sent(it["message"], cfg, it["key"])
                sent.append(it["key"])
            else:
                it["delivery_error"] = why
        else:
            q.append({"key": it["key"], "message": it["message"], "gate_tier": it["gate_tier"], "queued_at": now.isoformat()})
            queued.append(it["key"])
    if q:
        p = _queue_path(cfg)
        old = json.loads(p.read_text()) if p.exists() else []
        have = {x["key"] for x in old}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(old + [x for x in q if x["key"] not in have], indent=1))
    meta["sent"], meta["queued"] = sent, queued


def flush(cfg, base_dir, now_override=None, active_at=None, live=False):
    """Deliver queued chases when allowed (outside quiet hours, or the user is active). Dry run only lists them."""
    tz = cfgmod.get_tz(cfg["timezone"])
    now = cfgmod.now_in(tz, now_override)
    last = cfgmod.parse_dt(active_at, tz) if active_at else None
    p = _queue_path(cfg)
    q = json.loads(p.read_text()) if p.exists() else []
    if not q:
        return {"queued": 0, "sent": [], "note": "queue empty"}
    if not deliver_now(now, last, cfg):
        return {"queued": len(q), "sent": [], "note": "still quiet hours and the user is not active"}
    gate = Gate(cfgmod.state_dir(cfg) / "gate.json", write=live)
    sent, keep = [], []
    for x in q:
        ok, why = adapters.deliver(x["message"], cfg, base_dir, x["key"], dry=not live)
        if live and ok:
            gate.record(x["key"], x["gate_tier"])
            adapters.record_sent(x["message"], cfg, x["key"])
            sent.append(x["key"])
        elif not live:
            sent.append(x["key"])
        else:
            keep.append(x)
    if live:
        p.write_text(json.dumps(keep, indent=1))
    return {"queued": len(q), "sent": sent, "note": "dry run: nothing delivered" if not live else "delivered"}


def _rel(path, base_dir):
    try:
        return str(Path(path).resolve().relative_to(Path(base_dir).resolve()))
    except (ValueError, OSError):
        return os.path.basename(str(path))


def render_md(items, meta, base_dir="."):
    L = [f"Run: {meta['generated_at']}. Quiet hours now: {'yes' if meta['quiet_hours_now'] else 'no'}. User active in the window: {'YES' if meta['user_active'] else 'no'}. "
         f"A CHASE NOW goes: {'immediately' if meta['deliver_now'] else 'to the batch (queued)'}.", ""]
    if meta["activity"]:
        L.append("Activity evidence (newest first): " + "; ".join(f"{a['at']} {a['surface']}" for a in meta["activity"]))
        L.append("")
    L += ["| source | read ok | what it said |", "|---|---|---|"]
    for s in meta["sources"]:
        L.append(f"| {s['name']} | {'yes' if s['ok'] else 'NO'} | {s.get('note', '')} ({s['n']} candidates) |")
    c = meta["counts"]
    L += ["", f"**{meta['total']} candidates: CHASE NOW {c[CHASE]}, BATCH {c[BATCH]}, HOLD {c[HOLD]}, DROP {c[DROP]}.**"]
    for cls in ORDER:
        group = [i for i in items if i["triage"]["class"] == cls]
        if not group:
            continue
        L += ["", f"### {cls} ({len(group)})"]
        for i in group:
            t, p = i["triage"], i["triage"]["parts"]
            L += ["", f"**{i['title']}** `{i['key']}` ({i['source']})", f"- State: {i['state']}", f"- Why {cls}: {t['reason']}",
                  f"- Scores: importance {p['importance']} (money {p['money']}, deadline {p['deadline']}, blocks others {p['blocks_others']}, irreversible {p['irreversible']}); time-sensitive {p['time_sensitive']}",
                  f"- Already known: {p['user_knows']}", f"- Novelty gate: {p['novelty_gate']}" + (f"; {p['new_next_step']}" if "new_next_step" in p else "")]
            if t.get("action"):
                L.append(f"- Agent action: {t['action']}")
            if t.get("delivery"):
                L.append(f"- Delivery: {t['delivery']}")
            if i.get("artifact"):
                L.append(f"- Artifact: `{_rel(i['artifact'], base_dir)}`")
            if i.get("steps"):
                L.append("- Bite-sized steps (smallest first): " + " / ".join(f"{n + 1}. {s}" for n, s in enumerate(i["steps"][:3])))
            if i["owed_reply"] and cls == CHASE:
                L.append("- Message: none. The answer itself is the message: the agent writes it first and sends it as one reply. An announcement ('you have an unanswered message') would be a bare reminder.")
            if i.get("message"):
                w, probs = message.lint(i["message"])
                L += [f"- Message ({w} words{'; LINT: ' + ', '.join(probs) if probs else ', lint clean'}):", "", "```", i["message"], "```"]
    return "\n".join(L)
