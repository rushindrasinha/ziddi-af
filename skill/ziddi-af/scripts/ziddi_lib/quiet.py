"""Quiet hours, with the "unless the user is active" override."""
from datetime import timedelta


def _hm(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def in_quiet_hours(now, cfg):
    q = cfg["quiet_hours"]
    if not q.get("enabled", True):
        return False
    a, b, cur = _hm(q["start"]), _hm(q["end"]), now.hour * 60 + now.minute
    return (a <= cur < b) if a <= b else (cur >= a or cur < b)


def is_active(now, last_active, cfg):
    """True when the user did something on any surface within the active window."""
    if last_active is None:
        return False
    return timedelta(0) <= (now - last_active) <= timedelta(minutes=cfg["active_window_minutes"])


def deliver_now(now, last_active, cfg):
    """A chase goes out immediately outside quiet hours, or inside them when the user is active. Otherwise it queues."""
    return (not in_quiet_hours(now, cfg)) or is_active(now, last_active, cfg)
