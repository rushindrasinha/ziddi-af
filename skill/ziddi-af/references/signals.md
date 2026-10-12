# Signal sources: where chase candidates come from

You wire these in `ziddi.config.json` under `"signals"`. Every adapter turns something you already have (a task list, a job tracker, a chat log, a calendar, any command) into candidates. Nothing ships pointing at a real account.

```json
"signals": [
  {"adapter": "items",        "path": "tasks.json"},
  {"adapter": "jobs",         "path": "jobs.json"},
  {"adapter": "conversation", "path": "chat.jsonl"},
  {"adapter": "ics",          "path": "calendar.ics"},
  {"adapter": "command",      "command": ["python3", "my_inbox_headers.py"]}
]
```

Relative paths resolve against the folder that holds the config file.

## The candidate format (`items`, and what `command` must print)

A JSON list of objects. Only `id` and `title` are required.

| Field | Meaning |
|---|---|
| `id` | stable key for the item; the novelty gate and the "already told" check key on it |
| `title`, `state` | what it is, and what is true right now (one line) |
| `kind` | `item` (default), `followup`, `event` (an FYI, never chased), `noise` (dropped), `promise` |
| `deadline` | ISO date or `YYYY-MM-DD HH:MM` in your configured timezone |
| `money` | 0 none, 1 small, 2 real money or a partner relationship, 3 revenue path or six figures. Falls back to the keywords in `topics.money` |
| `blocks_others`, `irreversible` | each adds 2 to importance |
| `artifact` | path to the finished thing (a draft, a report). A chase needs this or a `recommendation` |
| `recommendation`, `steps`, `reply` | the recommended decision; steps smallest first; the one-token reply you want |
| `ask_terms` | words of the specific thing you will ask for ("discount", "percent"); the chase is "new" if the last mention did not contain them |
| `know_terms` | words that identify the item in earlier messages, for the "already told" check |
| `last_verified` | ISO date; older than `stale_days` (21) with no deadline soon means DROP |
| `waiting_on_user` | parked on the user: held instead of dropped when stale; also blocks any default action |
| `self_serve` | `{"action": "...", "reversible": true, "why": "..."}`: the agent can just do it. Becomes a done-receipt, not an ask |
| `needs_prep` | the agent must prepare the artifact before this can chase |
| `default_action` | `{"action": "...", "reversible": true, "after_hours": 6}`: a pre-agreed default for the 2nd and 3rd touch; ignored for items `waiting_on_user` |
| `noise_why`, `covered` | for `noise` and `promise` kinds |

## Built-in adapters

- **items**: a JSON file of candidates in the format above.
- **jobs**: a JSON list of `{"name", "status": "pending", "dispatched_at", "verify_after", "artifacts": [paths], "summary"}`. All artifacts present after dispatch means *finished* (a digest item); the window passed with artifacts missing means *overdue* (the agent checks it itself); inside the window means *running* (dropped; the tracker owns it). `landed_at` can pin the finish time.
- **conversation**: a JSONL transcript of `{"ts", "session", "role": "user|assistant", "text"}`. A session that ends on a user message more than 10 minutes old is an **owed reply** (the chase is the answer itself, and it is dropped when another stream already answered it or a job covers it). Assistant promises of later delivery with no follow-up become low-priority candidates.
- **ics**: a calendar file. Timed events in the next 48 h and all-day entries in the next 8 days. Words like *withdraw, signature, deadline, last day, expires* mark an irreversible deadline; other all-day entries are FYI and held.
- **command**: any command that prints a candidate list as JSON. This is the bridge to everything else: a mail client's unread-headers command, `gh issue list --json`, a CRM export, a script that reads your own database.

## Examples of wiring the bridge

Unread important mail, headers only (never read bodies for triage):

```bash
# my_inbox_headers.py: print [{"id": ..., "title": subject, "state": "unread since ...", "money": 2}]
```

GitHub issues assigned to you with a deadline label:

```bash
gh issue list --assignee @me --json number,title,labels,updatedAt \
  | python3 -c 'import json,sys; print(json.dumps([{"id": f"gh-{i["number"]}", "title": i["title"], "state": "open"} for i in json.load(sys.stdin)]))'
```

## "Does the user already know?"

The engine reads `known_logs` (JSONL rows of `{"ts", "text"}`) plus `$ZIDDI_HOME/sent.jsonl`, which `--live` delivery appends to. Point `known_logs` at anything else that records what your agent told the user. If it finds an earlier mention that already contains your `ask_terms`, the chase adds no new step and is held.

## Is the user active right now?

`"activity": {"adapter": "none"}` (default, treated as inactive), `{"adapter": "file", "path": "activity.jsonl"}` (any JSONL with a `ts` per user message), or `{"adapter": "command", "command": "..."}` printing an ISO timestamp. `--user-active-at "YYYY-MM-DD HH:MM"` overrides for one run.
