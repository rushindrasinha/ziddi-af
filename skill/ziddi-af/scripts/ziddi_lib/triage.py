"""Smart triage. Every candidate becomes exactly one of four classes, with the reason shown.

  CHASE NOW                   important + time-sensitive + not already known + not something the agent can do itself +
                              carries an artifact or a recommended decision + new information or a new next step.
  BATCH (digest)              worth telling the user, not worth an interrupt: finished jobs, prep items, deadlines still
                              far out, "I did it, done" receipts.
  HOLD UNTIL USER RAISES IT   parked, already known with nothing new, standing do-not-nag topics, touched already.
  DROP                        stale and unverified, closed, a bare reminder with no artifact and no next step.

Whether the agent can simply do it itself is a factor, not a fifth class: such items become a BATCH receipt or a DROP.
"""
import hashlib
import os
from datetime import timedelta

CHASE, BATCH, HOLD, DROP = "CHASE NOW", "BATCH (digest)", "HOLD UNTIL USER RAISES IT", "DROP"
ORDER = {CHASE: 0, BATCH: 1, HOLD: 2, DROP: 3}


def deadline_tier(hours, sunk_days=14):
    if hours is None:
        return "none"
    if hours < -sunk_days * 24:
        return "overdue-14d"
    if hours < -7 * 24:
        return "overdue-7d"
    if hours < 0:
        return "overdue"
    if hours <= 1:
        return "1h"
    if hours <= 24:
        return "24h"
    if hours <= 48:
        return "48h"
    if hours <= 168:
        return "7d"
    return "later"


def new_item(key, kind, title, state, **kw):
    it = {"key": key, "source": "", "kind": kind, "title": title, "state": state, "artifact": None, "recommendation": None,
          "steps": [], "reply": None, "mtype": "ACTION", "money": 0, "deadline": None, "blocks_others": False,
          "irreversible": False, "self_serve": None, "default_action": None, "waiting_on_user": False, "verified_age_days": None,
          "ask_terms": [], "all_terms": [], "know_terms": [], "evidence": [], "needs_prep": False, "owed_reply": False,
          "suppress": None, "covered": False, "landed_at": None, "asked_at": None, "noise_why": "", "msg_state": None, "default_note": None}
    it.update(kw)
    return it


def topic_flags(text, cfg):
    t = text.lower()
    money = max([v for k, v in cfg["topics"]["money"].items() if k.lower() in t] or [0])
    sup = next((s for s in cfg["topics"]["suppress"] if any(k.lower() in t for k in s.get("keywords", []))), None)
    return money, sup


def importance(it, hours, urgent_hours):
    imp = it["money"] * 2
    if hours is not None:
        imp += 4 if hours <= 24 else 3 if hours <= urgent_hours else 1 if hours <= 168 else 0
    imp += 2 if it["blocks_others"] else 0
    imp += 2 if it["irreversible"] else 0
    return imp


def fingerprint(it):
    """What we would SAY and with what artifact. Never volatile counters like '10 days overdue', or the gate would re-fire daily."""
    stamp = ""
    if it["artifact"] and os.path.exists(it["artifact"]):
        stamp = f"{os.path.basename(it['artifact'])}:{int(os.path.getmtime(it['artifact']))}"
    raw = "|".join([it["key"], stamp, it["recommendation"] or "", "|".join(it["steps"][:1])])
    return hashlib.sha1(raw.encode()).hexdigest()[:8]


def classify(it, ctx):
    now, cfg, gate, know = ctx["now"], ctx["cfg"], ctx["gate"], ctx["knowledge"]
    tcfg = cfg["triage"]
    hours = (it["deadline"] - now).total_seconds() / 3600 if it["deadline"] else None
    tier = deadline_tier(hours, tcfg["sunk_overdue_days"])
    imp = importance(it, hours, tcfg["urgent_hours"])
    urgent = (hours is not None and hours <= tcfg["urgent_hours"] and (hours >= -tcfg["sunk_overdue_days"] * 24 or it["money"] >= 3)) or it["owed_reply"]
    parts = {"importance": imp, "money": it["money"], "deadline": (f"{it['deadline']:%Y-%m-%d %H:%M} ({tier}, {hours:+.0f} h)" if hours is not None else "none"),
             "blocks_others": it["blocks_others"], "irreversible": it["irreversible"], "time_sensitive": urgent}

    # does the user already know?
    since = it.get("landed_at") or (now - timedelta(days=10))
    told = know.told([t for t in it["know_terms"] if t and len(t) > 3], since) if it["know_terms"] else None
    it["user_knows"] = told
    parts["user_knows"] = f"{told[0]}: \"{told[1][:110]}\"" if told else f"no earlier mention found since {since:%Y-%m-%d}"
    gtier = f"{fingerprint(it)}|{tier}"
    ok_gate, gwhy = gate.peek(it["key"], gtier, now.tzinfo)
    it["gate_tier"] = gtier
    parts["novelty_gate"] = gwhy
    touches = gate.touches(it["key"])
    new_step = True
    if told and it["ask_terms"]:
        new_step = not any(a.lower() in told[2].lower() for a in it["ask_terms"])
        parts["new_next_step"] = f"{'yes' if new_step else 'no'}: asks for {it['ask_terms'][:3]}; the last mention {'does not contain' if new_step else 'already contains'} it"

    def out(cls, why, delivery=None, action=None):
        return {"class": cls, "reason": why, "delivery": delivery, "action": action, "parts": parts}

    k = it["kind"]
    if it["suppress"] and not (hours is not None and hours <= 24):
        return out(HOLD, f"standing do-not-nag topic: {it['suppress'].get('why', 'configured to stay quiet')}")
    if k == "job_running":
        return out(DROP, "the job is still inside its window and running; the job tracker owns it. Nothing to tell yet.")
    age = it["verified_age_days"]
    if age is not None and age > cfg["stale_days"] and not (hours is not None and -2 < hours <= 168):
        if it["waiting_on_user"]:
            return out(HOLD, f"parked waiting on the user, {age:.0f} d with no fresh evidence: never resurface without fresh evidence, a time risk, or the user reopening it")
        return out(DROP, f"stale: last verified {age:.0f} d ago, no fresh evidence, no deadline in the next 7 d. A verify-first task for the agent, not a chase.")
    if k == "event":
        return out(HOLD, "an FYI entry the user put in their own calendar; they know it exists and no decision is attached")
    if k == "noise":
        return out(DROP, f"{it['noise_why'] or 'noise'}: not worth a chase or a prep")
    if k == "promise":
        if it["covered"]:
            return out(HOLD, "the promise is tracked by a job or watcher; nothing shows it was missed (precision over volume)")
        return out(DROP, "cannot verify non-delivery in any stream; a bare promise with no artifact is not a chase")

    if it["owed_reply"]:
        toks = it["ask_terms"]
        ans = know.told_all(toks[:2], it["asked_at"]) if len(toks) >= 2 else None
        job = next((n for n in ctx["jobs"] if any(t.lower() in n.lower() for t in it["all_terms"])), None)
        if ans:
            return out(DROP, f"answered elsewhere: {ans[0]} \"{ans[1][:90]}\"")
        if job:
            return out(DROP, f"already being handled by job '{job}'")
        if len(toks) < 2:
            return out(BATCH, "too little text to verify whether it was answered. A chase needs an answer to carry, so the agent reads that conversation now, does the task, and reports done.", "digest", "DO IT NOW: read context, finish, report done")
        if not ok_gate:
            return out(HOLD, f"the answer was already attempted: {gwhy}")
        return out(CHASE, "the user's own message has no reply anywhere searchable; answering is owed. The deliverable is the answer itself (self-serve: do it, then one line saying done).",
                   "now" if ctx["deliver_now"] else "queue to the batch", "ANSWER IT (self-serve)")

    if it["self_serve"] and it["self_serve"].get("reversible"):
        ss = it["self_serve"]
        if k in ("followup", "inbox") and (it["money"] >= 2 or it["deadline"] or it["needs_prep"]):
            if imp >= tcfg["chase_now_min_importance"] and urgent:
                return out(BATCH, f"high importance and time-critical, but it carries no artifact yet and a chase must carry one. The agent prepares first: {ss['action']}. Becomes CHASE NOW once the artifact exists.", "digest", "AUTO-DO (prep) then re-triage")
            return out(BATCH, f"the agent can do the prep itself ({ss.get('why', 'reversible, in its own lane')}): {ss['action']}. Report 'done, ready' in the digest; no ask.", "digest", "AUTO-DO then report done")
        return out(BATCH, f"the agent can do this itself ({ss.get('why', 'reversible, in its own lane')}): {ss['action']}.", "digest", "AUTO-DO then report done")

    if not it["artifact"] and not it["recommendation"]:
        if imp >= tcfg["chase_now_min_importance"]:
            return out(BATCH, f"important (score {imp}) but {'time-critical' if urgent else 'not yet inside the urgent window'}; no artifact or recommended decision exists, so it cannot chase yet. Prepare a decision memo; the next deadline tier ({tier} now) re-triages it.", "digest", "PREP then re-triage at the next tier")
        return out(DROP, f"no artifact, no recommendation, importance {imp}: a bare reminder is not a chase")

    if not ok_gate:
        return out(HOLD, gwhy)
    if told and not new_step and tier in ("none", "later", "7d"):
        return out(HOLD, f"the user already knows (last told {told[0]}) and this chase adds no new step")

    da = it["default_action"] if (it["default_action"] and it["default_action"].get("reversible") and not it["waiting_on_user"]) else None
    if touches >= 2:
        if da:
            return out(BATCH, f"two touches already and no reply. Third touch is never a louder repeat: take the pre-agreed reversible default ({da['action']}), then report done and how to undo it.", "digest", f"EXECUTE DEFAULT: {da['action']}")
        return out(HOLD, "two touches already; a third message would only be louder. Parked until the user raises it or something changes. (A gated action stays gated: silence is not consent.)")

    if imp >= tcfg["chase_now_min_importance"] and urgent:
        if touches == 1 and da:
            by = now + timedelta(hours=da.get("after_hours", 24))
            if it["deadline"] and it["deadline"] > now:
                by = min(by, it["deadline"] - timedelta(minutes=30))
            it["default_note"] = f"If I don't hear by {by:%a %H:%M}, I will {da['action']}. Reply 'hold' to stop it."
        why = f"importance {imp} and inside the urgent window ({tier}); carries an artifact and a recommended decision; {'new next step' if new_step else 'deadline tier changed'}; not self-serve"
        return out(CHASE, why, "now" if ctx["deliver_now"] else "queue to the batch")
    if imp >= tcfg["chase_now_min_importance"]:
        return out(BATCH, f"important (score {imp}) but not yet time-critical (deadline tier {tier}); digest now, becomes CHASE NOW inside the urgent window", "digest")
    if k == "job_landed":
        return out(BATCH, "a finished job with a verified artifact: tell the user, no decision is time-boxed", "digest")
    if imp >= tcfg["digest_min_importance"]:
        return out(BATCH, f"worth telling the user once (score {imp}), not worth an interrupt", "digest")
    return out(HOLD, f"low importance (score {imp}), no deadline, no artifact they need: waits for them to raise it")
