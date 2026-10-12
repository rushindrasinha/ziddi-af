"""Pluggable adapters: where candidates come from, how the agent knows what the user was already told, whether the user is
active, and how a chase is delivered. All stdlib. Nothing here points at a real account, channel or path: you wire your own.

Signal adapters  : items, jobs, conversation, ics, command   (config key "signals": [{"adapter": "...", ...}])
Activity adapters: none, file, command                        (config key "activity")
Delivery adapters: stdout, file, webhook                      (config key "delivery")
"""
import hashlib
import json
import os
import re
import subprocess
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config as cfgmod
from .triage import new_item, topic_flags

# ---------------------------------------------------------------- shared helpers


def _read_json_any(path):
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text[0] in "[{":
        try:
            d = json.loads(text)
            return d if isinstance(d, list) else d.get("items") or d.get("messages") or d.get("jobs") or []
        except ValueError:
            pass
    return [json.loads(ln) for ln in text.splitlines() if ln.strip().startswith("{")]


def item_from_dict(d, cfg, tz, now, source="items", base_dir="."):
    """Normalise a user-supplied raw candidate (see references/signals.md) into an internal item."""
    money_cfg, sup = topic_flags(" ".join(str(d.get(k, "")) for k in ("title", "state", "tags")), cfg)
    lv = cfgmod.parse_dt(d.get("last_verified"), tz)
    it = new_item(str(d.get("id") or d.get("key") or d.get("title")), d.get("kind", "item"), d.get("title", "(untitled)"), d.get("state", ""),
                  source=source, artifact=(str(cfgmod.resolve_path(d["artifact"], base_dir)) if d.get("artifact") else None), recommendation=d.get("recommendation"), steps=list(d.get("steps") or []),
                  reply=d.get("reply"), mtype=d.get("type", "ACTION"), money=int(d.get("money", money_cfg)),
                  deadline=cfgmod.parse_dt(d.get("deadline"), tz), blocks_others=bool(d.get("blocks_others")),
                  irreversible=bool(d.get("irreversible")), self_serve=d.get("self_serve"), default_action=d.get("default_action"),
                  waiting_on_user=bool(d.get("waiting_on_user")), verified_age_days=((now - lv).total_seconds() / 86400 if lv else None),
                  ask_terms=list(d.get("ask_terms") or []), know_terms=list(d.get("know_terms") or []),
                  needs_prep=bool(d.get("needs_prep")), suppress=sup, msg_state=d.get("msg_state"),
                  noise_why=d.get("noise_why", ""), covered=bool(d.get("covered")), owed_reply=bool(d.get("owed_reply")))
    return it


# ---------------------------------------------------------------- knowledge: what was the user already told?
class Knowledge:
    """Reads message logs (JSONL rows with ts + text) the agent has sent. The file delivery adapter writes one for you."""

    def __init__(self, paths, tz):
        self.tz = tz
        self.rows = []
        for p in paths:
            p = Path(p)
            if p.is_file():
                for r in _read_json_any(p):
                    t = cfgmod.parse_dt(r.get("ts"), tz)
                    if t and r.get("text"):
                        self.rows.append((t, str(r["text"])))
        self.rows.sort(key=lambda x: x[0], reverse=True)

    @staticmethod
    def _snip(text, term):
        i = max(text.lower().find(term.lower()), 0)
        return re.sub(r"\s+", " ", text[max(0, i - 60): i + 120]).strip()

    def told(self, terms, since):
        for t, text in self.rows:
            if t >= since and any(x.lower() in text.lower() for x in terms):
                hit = next(x for x in terms if x.lower() in text.lower())
                return (t.strftime("%Y-%m-%d %H:%M"), self._snip(text, hit), text)
        return None

    def told_all(self, terms, since):
        for t, text in self.rows:
            if t >= since and all(x.lower() in text.lower() for x in terms):
                return (t.strftime("%Y-%m-%d %H:%M"), self._snip(text, terms[0]), text)
        return None


# ---------------------------------------------------------------- activity: is the user around right now?
def last_user_activity(cfg, base_dir, tz, override=None):
    """Newest sign that the user did something on any surface -> list of (datetime, label), newest first."""
    ev = []
    a = cfg.get("activity", {"adapter": "none"})
    kind = a.get("adapter", "none")
    try:
        if kind == "file":
            rows = _read_json_any(cfgmod.resolve_path(a["path"], base_dir))
            for r in rows:
                t = cfgmod.parse_dt(r.get("ts"), tz)
                if t:
                    ev.append((t, a.get("label", "activity file")))
        elif kind == "command":
            out = subprocess.run(a["command"], shell=isinstance(a["command"], str), capture_output=True, text=True, timeout=20).stdout.strip()
            t = cfgmod.parse_dt(out.splitlines()[-1], tz) if out else None
            if t:
                ev.append((t, a.get("label", "activity command")))
    except Exception:
        pass
    if override:
        ev.append((override[0], override[1]))
    ev.sort(key=lambda x: x[0], reverse=True)
    return ev


# ---------------------------------------------------------------- signal adapters
def sig_items(spec, cfg, base_dir, tz, now):
    p = cfgmod.resolve_path(spec["path"], base_dir)
    rows = _read_json_any(p)
    items = [item_from_dict(r, cfg, tz, now, spec.get("name", "items"), base_dir) for r in rows]
    return items, {"name": spec.get("name", f"items:{p.name}"), "ok": True, "note": f"{len(items)} candidates from {p.name}"}


def sig_jobs(spec, cfg, base_dir, tz, now):
    p = cfgmod.resolve_path(spec["path"], base_dir)
    items = []
    for j in _read_json_any(p):
        if j.get("status", "pending") != "pending":
            continue
        name = j["name"]
        disp = cfgmod.parse_dt(j.get("dispatched_at"), tz)
        verify = cfgmod.parse_dt(j.get("verify_after"), tz)
        arts = [str(cfgmod.resolve_path(a, base_dir)) for a in j.get("artifacts", [])]
        landed_override = cfgmod.parse_dt(j.get("landed_at"), tz)  # lets examples and tests be deterministic
        fresh = [a for a in arts if os.path.exists(a) and (landed_override or not disp or datetime.fromtimestamp(os.path.getmtime(a), tz) >= disp)]
        money, sup = topic_flags(name + " " + j.get("summary", ""), cfg)
        if arts and len(fresh) == len(arts):
            newest = landed_override or max(datetime.fromtimestamp(os.path.getmtime(a), tz) for a in fresh)
            it = new_item(f"job:{name}", "job_landed", f"Job finished: {name}", f"All {len(arts)} declared artifacts exist (newest {newest:%Y-%m-%d %H:%M}). {j.get('summary', '')}".strip(),
                          source="jobs", artifact=fresh[0], money=money, know_terms=[name, os.path.basename(fresh[0])], mtype="WIN",
                          recommendation="review the artifact; the job is verified done", steps=[f"Open {os.path.basename(fresh[0])} (2 min)", "Say 'ship' or name the one thing to change"],
                          reply="ship / change <x>", landed_at=newest, suppress=sup)
        elif verify and now > verify:
            missing = [a for a in arts if a not in fresh]
            it = new_item(f"job:{name}", "job_overdue", f"Job overdue: {name}", f"The verify window ended {verify:%Y-%m-%d %H:%M}; {len(missing)} of {len(arts)} declared artifacts are missing or older than dispatch.",
                          source="jobs", money=money, mtype="ERROR", evidence=[f"missing: {os.path.basename(m)}" for m in missing[:3]], know_terms=[name], suppress=sup,
                          self_serve={"action": "check the job, restart or finish it", "why": "the agent's own job, reversible", "reversible": True})
        else:
            it = new_item(f"job:{name}", "job_running", f"Job in flight: {name}", "Still inside its window.", source="jobs", money=money, suppress=sup)
        items.append(it)
    return items, {"name": spec.get("name", f"jobs:{p.name}"), "ok": True, "note": f"{len(items)} pending jobs"}


_PROMISE = re.compile(r"(\b(?:i'?ll|i will|will)\s+(?:tell|ping|message|update|notify|let) you\b|\bkeep you posted\b|\breport back\b|\bget back to you\b|\bcheck back\b|"
                      r"\bas soon as\b[^.]{0,60}\b(?:lands?|ready|done|finish\w*|built)\b|\bthe moment\b|\bset a (?:watcher|reminder)\b|\bwill post (?:here|in)\b)", re.I)
_STOP = set("about which would should could there their these those where while please really because before after through between another everything something anything".split())


def sig_conversation(spec, cfg, base_dir, tz, now):
    """Owed replies (a conversation that ends on the user's message) and open promises, from a JSONL transcript."""
    p = cfgmod.resolve_path(spec["path"], base_dir)
    rows = [r for r in _read_json_any(p) if r.get("role") in ("user", "assistant") and r.get("text")]
    by = {}
    for r in rows:
        t = cfgmod.parse_dt(r.get("ts"), tz)
        if t:
            by.setdefault(r.get("session", "default"), []).append((t, r["role"], str(r["text"])))
    items = []
    for sid, ms in by.items():
        ms.sort(key=lambda x: x[0])
        t, role, text = ms[-1]
        prev_a = next((x[2] for x in reversed(ms[:-1]) if x[1] == "assistant"), "")
        if role == "user" and timedelta(minutes=10) <= (now - t) <= timedelta(hours=36) and len(text) < 1500:
            words = sorted({w.lower() for w in re.findall(r"[A-Za-z]{6,}", text) if w.lower() not in _STOP}, key=len, reverse=True)
            ctx = f" (replying to: \"{re.sub(chr(10), ' ', prev_a)[-110:]}\")" if prev_a else ""
            items.append(new_item(f"owed:{sid}", "owed_reply", "Unanswered message from the user",
                                  f"they wrote {(now - t).total_seconds() / 3600:.1f} h ago and the conversation ends on their message: \"{re.sub(chr(10), ' ', text)[:150]}\"{ctx}",
                                  source="conversation", owed_reply=True, mtype="QUESTION", asked_at=t, ask_terms=words[:4],
                                  all_terms=[w.lower() for w in re.findall(r"[A-Za-z]{5,}", text)],
                                  self_serve={"action": "answer it now", "why": "a reply is owed; the deliverable is the answer", "reversible": True}))
        for i, (t2, r2, x2) in enumerate(ms):
            if r2 != "assistant" or (now - t2) > timedelta(hours=24):
                continue
            pm = _PROMISE.search(x2)
            if not pm:
                continue
            later = next((m for m in ms[i + 1:] if m[1] == "assistant" and (m[0] - t2) >= timedelta(minutes=10)), None)
            nxt_user = next((m for m in ms[i + 1:] if m[1] == "user"), None)
            if later and (not nxt_user or later[0] < nxt_user[0]):
                continue
            money, sup = topic_flags(x2, cfg)
            items.append(new_item("promise:" + hashlib.sha1((str(sid) + t2.isoformat()).encode()).hexdigest()[:8], "promise", "Promised later delivery",
                                  f"{(now - t2).total_seconds() / 3600:.1f} h ago: \"{re.sub(chr(10), ' ', x2)[:150]}\"", source="conversation", mtype="FYI", money=money, suppress=sup,
                                  covered=bool(re.search(r"watcher|reminder|cron|job|session|post here|will post", x2, re.I))))
    return items, {"name": spec.get("name", f"conversation:{p.name}"), "ok": True, "note": f"{len(rows)} messages, {len(items)} candidates"}


def _ics_dt(val, tz):
    v = val.strip()
    if re.fullmatch(r"\d{8}", v):
        return datetime.strptime(v, "%Y%m%d").replace(hour=18, tzinfo=tz), True
    z = v.endswith("Z")
    d = datetime.strptime(v.rstrip("Z")[:15], "%Y%m%dT%H%M%S")
    return (d.replace(tzinfo=timezone.utc).astimezone(tz) if z else d.replace(tzinfo=tz)), False


def sig_ics(spec, cfg, base_dir, tz, now):
    p = cfgmod.resolve_path(spec["path"], base_dir)
    text = re.sub(r"\r?\n[ \t]", "", p.read_text(encoding="utf-8"))
    items = []
    for blk in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.S):
        f = dict(re.findall(r"^([A-Z]+)[^:\n]*:(.*)$", blk, re.M))
        if "DTSTART" not in f:
            continue
        start, allday = _ics_dt(f["DTSTART"], tz)
        title = f.get("SUMMARY", "(no title)")
        days = (start - now).total_seconds() / 86400
        if not (-0.05 <= days <= (8 if allday else 2)):
            continue
        money, sup = topic_flags(title, cfg)
        irrev = bool(re.search(r"withdraw|signature|deadline|last day|expires", title, re.I))
        need_prep = bool(re.search(r"meeting|call|interview|pitch|sign|review|deadline", title, re.I))
        if allday:
            it = new_item(f"cal:{start:%Y%m%d}:{title[:30]}", "deadline" if irrev else "event", title[:80], f"on {start:%a %d %b}, {int(days)} d away (all-day entry)", source="calendar",
                          deadline=start, money=(max(money, 3) if irrev else 0), irreversible=irrev, know_terms=[title[:25]], suppress=sup)
        else:
            it = new_item(f"cal:{f.get('UID', title)}", "meeting" if need_prep else "event", f"Upcoming: {title}", f"starts {start:%Y-%m-%d %H:%M}", source="calendar",
                          deadline=start, money=money if need_prep else 0, know_terms=[title], suppress=sup)
        items.append(it)
    return items, {"name": spec.get("name", f"ics:{p.name}"), "ok": True, "note": f"{len(items)} upcoming entries"}


def sig_command(spec, cfg, base_dir, tz, now):
    """The universal bridge: any command that prints a JSON list of raw candidates (see references/signals.md)."""
    cmd = spec["command"]
    r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=int(spec.get("timeout", 60)), cwd=str(base_dir))
    rows = json.loads(r.stdout or "[]")
    rows = rows if isinstance(rows, list) else rows.get("items", [])
    items = [item_from_dict(x, cfg, tz, now, spec.get("name", "command"), base_dir) for x in rows]
    return items, {"name": spec.get("name", "command"), "ok": r.returncode == 0, "note": f"{len(items)} candidates (exit {r.returncode})"}


SIGNALS = {"items": sig_items, "jobs": sig_jobs, "conversation": sig_conversation, "ics": sig_ics, "command": sig_command}


# ---------------------------------------------------------------- delivery adapters
def deliver(message, cfg, base_dir, key="", dry=True):
    """Send one chase. Returns (ok, detail). Dry run never calls an adapter."""
    d = cfg["delivery"]
    kind = d.get("adapter", "stdout")
    if dry:
        return True, f"dry run: would deliver via '{kind}'"
    if kind == "stdout":
        print(message)
        return True, "printed"
    if kind == "file":
        p = cfgmod.resolve_path(d.get("path", cfgmod.state_dir(cfg) / "outbox.jsonl"), base_dir)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "key": key, "text": message}) + "\n")
        return True, f"appended to {p.name}"
    if kind == "webhook":
        url = os.environ.get(d.get("webhook_url_env", "ZIDDI_WEBHOOK_URL"))
        if not url:
            return False, f"webhook adapter selected but ${d.get('webhook_url_env', 'ZIDDI_WEBHOOK_URL')} is not set"
        body = {"discord": {"content": message}, "slack": {"text": message}}.get(d.get("payload", "generic"), {"text": message, "key": key})
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return 200 <= resp.status < 300, f"HTTP {resp.status}"
        except Exception as e:  # one failure means wrong address or channel: report it, never retry blind
            return False, f"send failed once, not retried: {e.__class__.__name__}"
    return False, f"unknown delivery adapter {kind!r}"


def record_sent(message, cfg, key=""):
    """Append what was sent to the knowledge log, so the next run knows the user was told."""
    p = cfgmod.state_dir(cfg) / "sent.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "key": key, "text": message}) + "\n")
