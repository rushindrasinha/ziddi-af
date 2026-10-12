"""Give-up detector. Deterministic, stdlib, no model.

A give-up is language telling the user a thing cannot be done, is blocked, does not work, or that only they can do it.
Such a reply is allowed only if it cites an attempt-log id (zid-YYYYMMDD-xxxx) whose verdict is exhausted, gated or budget-stop.

Never flagged: asking for approval, a refused guardrail action, quoted logs and code blocks, negations, conditionals,
and a failure narrated together with its recovery. Precision is favoured over recall (see references/giveup_testset.txt).
"""
import re

from . import store

ID_RE = re.compile(r"\bzid-\d{8}-[0-9a-f]{4}\b")

# (class, strong, regex). Strong hits flag on their own; weak hits are evidence only.
PATTERNS = [
    ("cant", True, re.compile(r"\b(?:i|we)(?:\s+(?:really|still|just|simply))?\s*(?:can'?t|cannot|can not|couldn'?t|am unable to|'m unable to|are unable to|won'?t be able to|am not able to|'m not able to)\b(?!\s+(?:wait|stress|overstate|help but|say for sure|tell|see|confirm|know|say|judge|determine|be sure|just repeat|unilateral|skip))", re.I)),
    ("epistemic", False, re.compile(r"\b(?:i|we)\s*(?:can'?t|cannot|couldn'?t)\s+(?:tell|see|confirm|know|say|judge|determine|be sure)\b", re.I)),
    ("unable", True, re.compile(r"\b(?:i|we|am|are|'m)\s*(?:unable|not able) to (?!tell|say|see|confirm|know)\w+", re.I)),
    ("not_working", True, re.compile(r"\b(?:didn'?t|did not|still doesn'?t|still won'?t|still isn'?t|never) work(?:ed|ing)?\b|\b(?:it|this|that) (?:doesn'?t|does not|won'?t|isn'?t|is not) work(?:ing)?\b|\bstopped working\b|\b(?:still )?not working\b", re.I)),
    ("blocked", True, re.compile(r"\b(?:i'?m|we'?re|i am|we are|it'?s|still|currently|and|is|are)\s+(?:completely\s+|fully\s+|genuinely\s+)?blocked (?:on|by)\b|\b(?:i'?m|we'?re|i am|we are|it'?s|still|currently)\s+(?:completely\s+|fully\s+|genuinely\s+)?blocked\b|(?:^|[.;:\-—*]\s*)\**blocked (?:on|by)\b|\bhard[- ]blocked\b", re.I)),
    ("only_you", True, re.compile(r"\bonly (?:you|the user|the owner) (?:can|could|are able|have)\b|\b(?:needs?|requires?|need) (?:you|the user) to (?:log ?in|sign ?in|click|run|open|do|install|grant|enable|unlock|plug|scan|connect|paste|copy|manually|raise|restart|relaunch|cancel|relink)\b|\byou(?:'ll| will)? (?:need|have) to (?:log ?in|sign ?in|click|run|open|do (?:it|this) (?:yourself|manually)|install|grant|enable|unlock|paste|manually)\b|\bmanual(?:ly)? (?:step|action|intervention)\b|\b(?:i'?d|i) need you to (?!approve|decide|confirm)\w+|\b(?:one-time )?human (?:action|step|hands)\b|\b(?:needs?|requires?) a human\b", re.I)),
    ("no_way", True, re.compile(r"\b(?:genuinely inaccessible|inaccessible to me|lacks? the (?:binding|access|permission|credential)|not possible|(?<!mathematically )impossible|there(?:'s| is) no (?:way|api|route|path|option|endpoint)|no (?:way|api) to\b|no supported (?:way|path)|not (?:supported|exposed|available) (?:by|via|in|through))", re.I)),
    ("no_access", False, re.compile(r"\b(?:no|don'?t have|lack|without|missing) (?:the )?(?:access|permission|credentials?|token|scope|login)\b|\b(?:403|401|permission denied|unauthori[sz]ed)\b", re.I)),
    ("failed", False, re.compile(r"\bfailed (?:to|with)\b|\bcouldn'?t (?:access|reach|find|get|log|connect|complete|do|open|load|fetch|read)\b|\bno (?:result|match|data|response)s?\b|\btimed? ?out\b|\bnothing (?:came|worked|found)\b", re.I)),
    ("shrug", False, re.compile(r"\bunfortunately\b|\bnot sure (?:how|if|whether)\b|\bno idea\b|\blimitation\b|\bnot something i can\b|\bbeyond (?:what i|my)\b", re.I)),
]
# A failure narrated alongside its fix is a status report, not a give-up.
RECOVERED = re.compile(r"\b(?:queued|instead of|so the next|but i (?:have|got|did|found|made|can)|fixed|resolved|worked around|workaround|now works?|now (?:runs|passes|loads)|so i (?:used|switched|tried|re-?ran|went|built|wrote)|instead,? i|switched to|fell back|fallback|retried and|re-?ran (?:it )?(?:and|with)|succeeded|recovered|done[:.!]|verified|passes|passed)\b", re.I)
# Approval and guardrail language: a gate is not an obstacle.
GATE = re.compile(r"\b(?:approv(?:e|al|ed)|go-?ahead|sign-?off|your call|your decision|need(?:s)? (?:a |your )?decision|which (?:one|option)|reply (?:1|yes|no|with)|guardrail|hard rule|policy|production (?:change|guardrail)|social[- ]publish|won'?t (?:publish|post|send|delete|spend)|will not (?:publish|post|send|delete|spend)|not (?:going to )?(?:publish|post|send|delete)|destructive|irreversible|unilateral\w*|bypass|override|supervis\w+|security (?:step|check|prompt)|safety rule|decisions?|licen[cs]e\w*)\b", re.I)
NEG_BEFORE = re.compile(r"(?:\bnot|n't|\bno|\bnothing|\bnever|\bwithout|\bnone|\bunblocked|\bresolved|\bwas|\bwere|\bno longer|\bonce)\W+(?:\w+\W+){0,2}$", re.I)
COND_BEFORE = re.compile(r"\b(?:where|why|how|if|when|unless|whether|says?|said|warns?|note|because|so that|even if|in case)\b[^.\n]{0,50}$", re.I)
DIGEST_HEAD = re.compile(r"^\s*(?:\*\*)?(?:daily digest|status digest|waiting on you|\d{1,2}:\d{2}\b)", re.I)
FENCE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`\n]+`")
QUOTE = re.compile(r"^\s*>.*$", re.M)
QUOTED = re.compile(r"[\"“][^\"”\n]{3,200}[\"”]")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def clean(text):
    text = QUOTED.sub(" ", FENCE.sub(" ", text))
    return INLINE.sub(" ", QUOTE.sub(" ", text))


def analyze(text):
    if DIGEST_HEAD.match(text):
        return {"hits": [], "weak_unflagged": [], "exempt": [{"class": "digest", "exempt": "status-digest"}]}
    sents = [s.strip() for s in SENT_SPLIT.split(clean(text)) if s.strip()]
    raw, exempt = [], []
    for i, s in enumerate(sents):
        window = s + " " + (sents[i + 1] if i + 1 < len(sents) else "")
        for cls, strong, rx in PATTERNS:
            m = rx.search(s)
            if not m:
                continue
            if NEG_BEFORE.search(s[max(0, m.start() - 40):m.start()]) or COND_BEFORE.search(s[max(0, m.start() - 60):m.start()]):
                continue
            hit = {"class": cls, "strong": strong, "match": m.group(0), "sentence": s[:240]}
            if RECOVERED.search(window):
                hit["exempt"] = "recovered"
                exempt.append(hit)
            elif GATE.search(window) and cls in ("only_you", "blocked", "cant", "unable", "no_way"):
                hit["exempt"] = "gate"
                exempt.append(hit)
            else:
                raw.append(hit)
    strong = [h for h in raw if h["strong"]]
    return {"hits": strong, "weak_unflagged": [h for h in raw if not h["strong"]], "exempt": exempt}


def find_giveups(text):
    return analyze(text)["hits"]


def decide(text, attempts_path=None, verify=False):
    a = analyze(text)
    ids = ID_RE.findall(text)
    out = {"giveup": bool(a["hits"]), "hits": a["hits"], "weak_unflagged": a["weak_unflagged"], "exempt": a["exempt"], "attempt_ids": ids}
    if not a["hits"]:
        out.update(verdict="ok", reason="no give-up language")
    elif not ids:
        out.update(verdict="flag", reason="give-up language and no attempt-log id (zid-YYYYMMDD-xxxx)")
    elif verify:
        bad = [why for z in ids for ok, why in [store.verify_id(z, attempts_path)] if not ok]
        if len(bad) == len(ids):
            out.update(verdict="flag", reason="cited attempt id invalid: " + "; ".join(bad))
        else:
            out.update(verdict="ok", reason="give-up backed by an attempt log")
    else:
        out.update(verdict="ok", reason="give-up cites an attempt id (not verified; add --verify)")
    return out
