# Chase triage: the decision table

The code is `skill/ziddi-af/scripts/ziddi_lib/triage.py` (`classify`). First match wins.

| Order | Test | Class |
|---|---|---|
| 1 | Matches a standing do-not-nag topic (`topics.suppress`) and the deadline is not inside 24 h | HOLD |
| 2 | A job still inside its verify window | DROP |
| 3 | Stale: last verified over `stale_days` and no deadline inside 7 days. `waiting_on_user` rows are held (never resurface without fresh evidence); the rest are dropped | HOLD / DROP |
| 4 | An FYI calendar entry the user made themselves | HOLD |
| 5 | Noise (cold outreach, unknown sender with no money, legal or deadline word) | DROP |
| 5b | A promise of later delivery: tracked by a job or watcher gives HOLD; untracked and unverifiable gives DROP | HOLD / DROP |
| 6 | Owed reply: answered in another stream, or a running job covers it | DROP |
| 7 | Owed reply with too little text to verify | BATCH: read the conversation, do it, report done |
| 8 | Owed reply, verified unanswered, not tried before | CHASE NOW, and the message *is* the answer (no announcement) |
| 9 | The agent can do it itself (reversible, in its lane, no gate) | BATCH receipt "did it, done"; prep first when the chase would lack an artifact |
| 10 | No artifact and no recommendation | important (score 5 or more): BATCH, prepare a decision memo, re-triage at the next deadline tier. Otherwise DROP |
| 11 | Novelty gate: identical fingerprint and deadline tier as the last touch | HOLD |
| 12 | The user already knows and the chase adds no new step and no tier change | HOLD |
| 13 | Two touches already: a reversible `default_action` exists and the item is not `waiting_on_user` | BATCH: execute the default, report done and how to undo. Otherwise HOLD (never a louder repeat) |
| 14 | Importance 5 or more and inside the urgent window (48 h by default; overdue under 14 days, or overdue with money 3) | CHASE NOW (the 2nd touch announces the default, if any) |
| 15 | Importance 5 or more, deadline further out | BATCH, becomes CHASE NOW inside the window |
| 16 | A finished job with a verified artifact | BATCH |
| 17 | Importance 2 to 4 | BATCH |
| 18 | Anything else | HOLD |

## Importance

`2 x money` + deadline (inside 24 h: 4, inside 48 h: 3, inside 7 days: 1) + 2 if it blocks others + 2 if irreversible. 5 or more is high. All thresholds are in `"triage"` in the config.

## Delivery is not a class

CHASE NOW goes out immediately when the user is active or it is outside quiet hours; otherwise it queues for the batch time.
