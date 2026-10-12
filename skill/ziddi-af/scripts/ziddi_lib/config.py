"""Config: one JSON file, sane defaults. Everything user-specific lives here, nothing is hard-coded."""
import copy
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULTS = {
    "schema_version": 1,
    "timezone": "UTC",
    "state_dir": "~/.ziddi",
    "quiet_hours": {"enabled": True, "start": "00:00", "end": "06:00", "batch_at": "06:00"},
    "active_window_minutes": 30,
    "stale_days": 21,
    "attempts": {"min_mechanisms": 4, "min_rungs": 3, "required_rungs": ["assets", "memory"], "budget_minutes": 20},
    "triage": {
        "chase_now_min_importance": 5,
        "digest_min_importance": 2,
        "urgent_hours": 48,
        "sunk_overdue_days": 14,
        "max_message_words": 60,
    },
    "topics": {
        "money": {"invoice": 2, "payment": 2, "contract": 3, "sponsor": 2, "renewal": 2, "tax": 2, "legal": 2},
        "suppress": [],
    },
    "signals": [],
    "known_logs": [],
    "activity": {"adapter": "none"},
    "delivery": {"adapter": "stdout", "webhook_url_env": "ZIDDI_WEBHOOK_URL", "payload": "generic"},
}


def deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def state_dir(cfg=None):
    raw = os.environ.get("ZIDDI_HOME") or (cfg or DEFAULTS)["state_dir"]
    return Path(os.path.expanduser(raw))


def find_config(explicit=None):
    cands = [explicit, os.environ.get("ZIDDI_CONFIG"), "ziddi.config.json",
             str(state_dir() / "config.json")]
    for c in cands:
        if c and Path(os.path.expanduser(c)).is_file():
            return Path(os.path.expanduser(c)).resolve()
    return None


def load(explicit=None):
    """-> (cfg, base_dir). base_dir resolves relative paths in the config; the cwd when there is no file."""
    p = find_config(explicit)
    if not p:
        return copy.deepcopy(DEFAULTS), Path.cwd()
    return deep_merge(DEFAULTS, json.loads(p.read_text(encoding="utf-8"))), p.parent


def resolve_path(raw, base_dir):
    p = Path(os.path.expanduser(str(raw)))
    return p if p.is_absolute() else (Path(base_dir) / p)


_OFFSET = re.compile(r"^(?:UTC)?([+-])(\d{1,2}):?(\d{2})?$")


def get_tz(name):
    """IANA name via zoneinfo when available, else UTC or a fixed offset like +05:30."""
    if not name or name.upper() == "UTC":
        return timezone.utc
    m = _OFFSET.match(name)
    if m:
        sign = -1 if m.group(1) == "-" else 1
        return timezone(sign * timedelta(hours=int(m.group(2)), minutes=int(m.group(3) or 0)))
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        return timezone.utc


def parse_dt(value, tz):
    """ISO date or datetime (also 'YYYY-MM-DD HH:MM', trailing Z) -> aware datetime in tz. None on failure."""
    if not value:
        return None
    s = str(value).strip().replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        try:
            d = datetime.strptime(s[:16], "%Y-%m-%d %H:%M")
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=tz)
    return d.astimezone(tz)


def now_in(tz, override=None):
    return parse_dt(override, tz) if override else datetime.now(tz)
