"""Attempt log: append-only JSONL, one row per attempt or verdict. A give-up must cite an id from here."""
import hashlib
import json
import os
import shlex
from datetime import datetime
from pathlib import Path

from . import config as cfgmod

RUNGS = ["fix-cause", "tool", "path", "assets", "memory", "web", "decompose", "adjacent"]
MULTIPLEX = {"git", "gh", "docker", "npm", "pip", "python3", "python", "node", "ssh", "bash", "sh", "make", "cargo", "go", "kubectl"}


def log_path(cfg=None):
    override = os.environ.get("ZIDDI_ATTEMPTS")
    return Path(override) if override else cfgmod.state_dir(cfg) / "attempts.jsonl"


def read_rows(path):
    if not Path(path).exists():
        return []
    out = []
    for ln in Path(path).read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(ln))
        except ValueError:
            pass
    return out


def append(path, row):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    row["schema_version"] = 1
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def new_id(goal, now):
    return f"zid-{now:%Y%m%d}-" + hashlib.sha1((goal + now.isoformat()).encode()).hexdigest()[:4]


def mechanism_key(rung, did, cmd=None, mechanism=None):
    """Distinctness: an explicit mechanism, else the binary (plus subcommand for multiplexers). New flags are not a new mechanism."""
    if mechanism:
        return mechanism.strip().lower()
    if cmd:
        try:
            toks = shlex.split(cmd)
        except ValueError:
            toks = cmd.split()
        if toks:
            binary = os.path.basename(toks[0]).lower()
            if binary in MULTIPLEX:
                rest = [t for t in toks[1:] if not t.startswith("-") and "://" not in t and "=" not in t]
                return " ".join([binary] + rest[:1])
            return binary
    return f"{rung}:{did[:30].lower()}"


def attempts_for(rows, zid):
    return [r for r in rows if r.get("id") == zid and r.get("kind") == "attempt"]


def elapsed_minutes(att):
    spent = sum(r.get("cost_s") or 0 for r in att)
    if len(att) < 2:
        return spent / 60
    t0 = datetime.fromisoformat(att[0]["ts"])
    t1 = datetime.fromisoformat(att[-1]["ts"])
    return max((t1 - t0).total_seconds(), spent) / 60


def ladder_problems(att, cfg):
    """Why this id may not be called `exhausted` yet. Empty list = it may."""
    a = cfg["attempts"]
    mechs = {r["mechanism"] for r in att if r["result"] != "ok"}
    rungs = {r["rung"] for r in att}
    probs = []
    if len(mechs) < a["min_mechanisms"]:
        probs.append(f"{len(mechs)} distinct mechanisms, need {a['min_mechanisms']}")
    if len(rungs) < a["min_rungs"]:
        probs.append(f"{len(rungs)} rungs used, need {a['min_rungs']}")
    for must in a["required_rungs"]:
        if must not in rungs:
            hint = {"assets": "existing scripts, MCP servers, credentials in your own setup",
                    "memory": "memory, notes and past transcripts for a prior working path"}.get(must, must)
            probs.append(f"rung '{must}' never tried ({hint})")
    if any(r["result"] == "ok" for r in att):
        probs.append("an attempt succeeded: the outcome is `solved`, not `exhausted`")
    return probs


def verify_id(zid, path, cfg=None):
    """(ok, reason): the id must exist and its latest verdict must be exhausted, gated or budget-stop."""
    rows = read_rows(path)
    mine = [r for r in rows if r.get("id") == zid]
    if not mine:
        return False, f"{zid} not in the attempt log"
    verdicts = [r for r in mine if r.get("kind") == "verdict"]
    if not verdicts:
        return False, f"{zid} has attempts but no verdict yet (run attempts.py verdict)"
    v = verdicts[-1]["verdict"]
    if v not in ("exhausted", "gated", "budget-stop"):
        return False, f"{zid} verdict is {v!r}; a give-up needs exhausted, gated or budget-stop"
    return True, "ok"
