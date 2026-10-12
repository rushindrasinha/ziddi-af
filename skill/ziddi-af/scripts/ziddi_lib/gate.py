"""Cooldown and dedupe gate. Bundled so ziddi-af has no dependency on any alerting library.

A chase about an item is allowed only if the item has never been touched, or what we would say or the deadline tier changed
since the last touch. An unchanged item never repeats, however much time passes: silence from the user is not a reason to
say the same thing louder. State is one small JSON file: {key: {"tier": str, "ts": float, "touches": int}}.
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path


class Gate:
    def __init__(self, path, write=False):
        self.path = Path(path)
        self.write = write
        try:
            self.state = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.state = {}

    def peek(self, key, tier, tz=None):
        """(allowed, why). Never writes."""
        prev = self.state.get(key)
        if not prev:
            return True, "first touch"
        when = datetime.fromtimestamp(prev["ts"], tz).strftime("%Y-%m-%d %H:%M")
        if prev.get("tier") != tier:
            return True, f"new information (changed since the last touch at {when})"
        return False, f"identical info already sent {when} (an unchanged item never repeats)"

    def touches(self, key):
        return int((self.state.get(key) or {}).get("touches", 0))

    def last_ts(self, key):
        return (self.state.get(key) or {}).get("ts")

    def record(self, key, tier, now_ts=None):
        if not self.write:
            return
        prev = self.state.get(key) or {}
        self.state[key] = {"tier": tier, "ts": now_ts or time.time(), "touches": int(prev.get("touches", 0)) + 1}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state), encoding="utf-8")
        os.replace(tmp, self.path)
