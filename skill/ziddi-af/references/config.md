# ziddi.config.json

Looked up in this order: `--config`, `$ZIDDI_CONFIG`, `./ziddi.config.json`, `$ZIDDI_HOME/config.json` (default `~/.ziddi/config.json`). No file means defaults. Keys you omit keep their defaults.

| Key | Default | Meaning |
|---|---|---|
| `timezone` | `"UTC"` | IANA name (`"Europe/Berlin"`) or a fixed offset (`"+05:30"`). Quiet hours and deadlines use it. |
| `state_dir` | `"~/.ziddi"` | Where the attempt log, gate, queue and sent log live. `$ZIDDI_HOME` overrides. |
| `quiet_hours` | `{enabled: true, start: "00:00", end: "06:00", batch_at: "06:00"}` | Chases queue inside this window unless the user is active. A window that wraps midnight (`22:00` to `07:00`) works. |
| `active_window_minutes` | `30` | The user counts as active if they did something on any surface this recently. |
| `stale_days` | `21` | Unverified longer than this with no deadline soon is dropped or parked. |
| `attempts` | `{min_mechanisms: 4, min_rungs: 3, required_rungs: ["assets","memory"], budget_minutes: 20}` | The ladder rules for `exhausted` and `budget-stop`. |
| `triage` | `{chase_now_min_importance: 5, digest_min_importance: 2, urgent_hours: 48, sunk_overdue_days: 14}` | Thresholds. |
| `topics.money` | a few words (`invoice`, `contract`, ...) | Keyword to money level (0 to 3). Add your own clients, deals, renewals. |
| `topics.suppress` | `[]` | `[{"keywords": [...], "why": "..."}]`: standing do-not-nag topics, held unless a deadline is inside 24 h. |
| `signals` | `[]` | Signal adapters (see signals.md). |
| `known_logs` | `[]` | Extra JSONL logs of what the agent already told the user. |
| `activity` | `{adapter: "none"}` | How to tell the user is active right now. |
| `delivery` | `{adapter: "stdout"}` | How a chase leaves (see delivery.md). |

Environment: `ZIDDI_HOME`, `ZIDDI_CONFIG`, `ZIDDI_ATTEMPTS` (path of the attempt log), `ZIDDI_OFF=1` (disable the hooks in a session).
