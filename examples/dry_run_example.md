Run: 2026-03-10 05:10 UTC. Quiet hours now: yes. User active in the window: YES. A CHASE NOW goes: immediately.

Activity evidence (newest first): 2026-03-10 04:50 operator-supplied

| source | read ok | what it said |
|---|---|---|
| your task list | yes | 8 candidates from items.example.json (8 candidates) |
| background jobs | yes | 3 pending jobs (3 candidates) |
| conversation log | yes | 8 messages, 4 candidates (4 candidates) |
| calendar file | yes | 3 upcoming entries (3 candidates) |

**18 candidates: CHASE NOW 3, BATCH 6, HOLD 3, DROP 6.**

### CHASE NOW (3)

**Harbor & Pine renewal quote** `renewal-harbor-pine` (your task list)
- State: Renewal quote is drafted; the discount percent is still blank and the offer lapses on the 11th.
- Why CHASE NOW: importance 9 and inside the urgent window (48h); carries an artifact and a recommended decision; new next step; not self-serve
- Scores: importance 9 (money 3, deadline 2026-03-11 17:00 (48h, +36 h), blocks others False, irreversible False); time-sensitive True
- Already known: 2026-03-09 14:00: "Reminder: the Harbor & Pine renewal needs your sign-off on terms before it lapses."
- Novelty gate: first touch; yes: asks for ['discount', 'percent']; the last mention does not contain it
- Delivery: now
- Artifact: `artifacts/renewal_quote_draft.md`
- Bite-sized steps (smallest first): 1. Send me the discount percent you will give (30 seconds) / 2. Read the draft (2 min) / 3. Say 'go' and I queue the exact text for you to send
- Message (40 words, lint clean):

```
[ACTION] Harbor & Pine renewal quote
State: Renewal quote is drafted; the discount percent is still blank and the offer lapses on the 11th.
Next: Send me the discount percent you will give (30 seconds)
Reply: the number, or 'hold'
```

**Pick the dentist slot** `dentist-slot` (your task list)
- State: Two slots left for tomorrow; the clinic holds them until 20:00 tonight.
- Why CHASE NOW: importance 6 and inside the urgent window (24h); carries an artifact and a recommended decision; new next step; not self-serve
- Scores: importance 6 (money 1, deadline 2026-03-10 20:00 (24h, +15 h), blocks others False, irreversible False); time-sensitive True
- Already known: no earlier mention found since 2026-02-28
- Novelty gate: first touch
- Delivery: now
- Bite-sized steps (smallest first): 1. Tell me 'yes' or 'other'
- Message (28 words, lint clean):

```
[ACTION] Pick the dentist slot
State: Two slots left for tomorrow; the clinic holds them until 20:00 tonight.
Next: Tell me 'yes' or 'other'
Reply: yes / other
```

**Unanswered message from the user** `owed:s1` (conversation)
- State: they wrote 3.2 h ago and the conversation ends on their message: "can you compare the three hosting providers on price and uptime and tell me which one to pick?" (replying to: "The three hosting quotes are in the shared sheet.")
- Why CHASE NOW: the user's own message has no reply anywhere searchable; answering is owed. The deliverable is the answer itself (self-serve: do it, then one line saying done).
- Scores: importance 0 (money 0, deadline none, blocks others False, irreversible False); time-sensitive True
- Already known: no earlier mention found since 2026-02-28
- Novelty gate: first touch
- Agent action: ANSWER IT (self-serve)
- Delivery: now
- Message: none. The answer itself is the message: the agent writes it first and sends it as one reply. An announcement ('you have an unanswered message') would be a bare reminder.

### BATCH (digest) (6)

**Tax filing: last day to withdraw the extension request** `cal:20260317:Tax filing: last day to withdr` (calendar)
- State: on Tue 17 Mar, 7 d away (all-day entry)
- Why BATCH (digest): important (score 8) but not yet inside the urgent window; no artifact or recommended decision exists, so it cannot chase yet. Prepare a decision memo; the next deadline tier (later now) re-triages it.
- Scores: importance 8 (money 3, deadline 2026-03-17 18:00 (later, +181 h), blocks others False, irreversible True); time-sensitive False
- Already known: no earlier mention found since 2026-02-28
- Novelty gate: first touch
- Agent action: PREP then re-triage at the next tier
- Delivery: digest

**Northwind Studios invoice question** `northwind-invoice` (your task list)
- State: Northwind asked which PO number to put on invoice 2214; no reply yet.
- Why BATCH (digest): the agent can do the prep itself (a draft is reversible and in the agent's own lane): draft the reply with the PO number found in last quarter's thread. Report 'done, ready' in the digest; no ask.
- Scores: importance 5 (money 2, deadline 2026-03-16 12:00 (7d, +151 h), blocks others False, irreversible False); time-sensitive False
- Already known: no earlier mention found since 2026-02-28
- Novelty gate: first touch
- Agent action: AUTO-DO then report done
- Delivery: digest

**Staging TLS certificate expires in 9 days** `tls-cert-staging` (your task list)
- State: Certificate renews automatically only if the DNS token is valid.
- Why BATCH (digest): the agent can do this itself (reversible, in the agent's own infrastructure): run the renewal against staging and verify the new expiry.
- Scores: importance 2 (money 1, deadline 2026-03-19 00:00 (later, +211 h), blocks others False, irreversible False); time-sensitive False
- Already known: no earlier mention found since 2026-02-28
- Novelty gate: first touch
- Agent action: AUTO-DO then report done
- Delivery: digest

**Job finished: render-demo-video** `job:render-demo-video` (jobs)
- State: All 1 declared artifacts exist (newest 2026-03-10 02:12). 62 s render, two cuts flagged for review.
- Why BATCH (digest): a finished job with a verified artifact: tell the user, no decision is time-boxed
- Scores: importance 0 (money 0, deadline none, blocks others False, irreversible False); time-sensitive False
- Already known: no earlier mention found since 2026-03-10
- Novelty gate: first touch
- Delivery: digest
- Artifact: `artifacts/demo_render_notes.md`
- Bite-sized steps (smallest first): 1. Open demo_render_notes.md (2 min) / 2. Say 'ship' or name the one thing to change

**Job overdue: nightly-backup-check** `job:nightly-backup-check` (jobs)
- State: The verify window ended 2026-03-10 03:00; 1 of 1 declared artifacts are missing or older than dispatch.
- Why BATCH (digest): the agent can do this itself (the agent's own job, reversible): check the job, restart or finish it.
- Scores: importance 0 (money 0, deadline none, blocks others False, irreversible False); time-sensitive False
- Already known: no earlier mention found since 2026-02-28
- Novelty gate: first touch
- Agent action: AUTO-DO then report done
- Delivery: digest

**Unanswered message from the user** `owed:s4` (conversation)
- State: they wrote 2.2 h ago and the conversation ends on their message: "ok you do it too" (replying to: "Sent the summary to the team channel.")
- Why BATCH (digest): too little text to verify whether it was answered. A chase needs an answer to carry, so the agent reads that conversation now, does the task, and reports done.
- Scores: importance 0 (money 0, deadline none, blocks others False, irreversible False); time-sensitive True
- Already known: no earlier mention found since 2026-02-28
- Novelty gate: first touch
- Agent action: DO IT NOW: read context, finish, report done
- Delivery: digest

### HOLD UNTIL USER RAISES IT (3)

**Sign the NDA from Lumen Coffee Co.** `nda-lumen` (your task list)
- State: Waiting on you since January.
- Why HOLD UNTIL USER RAISES IT: parked waiting on the user, 59 d with no fresh evidence: never resurface without fresh evidence, a time risk, or the user reopening it
- Scores: importance 2 (money 1, deadline none, blocks others False, irreversible False); time-sensitive False
- Already known: no earlier mention found since 2026-02-28
- Novelty gate: first touch

**Team offsite** `cal:20260313:Team offsite` (calendar)
- State: on Fri 13 Mar, 3 d away (all-day entry)
- Why HOLD UNTIL USER RAISES IT: an FYI entry the user put in their own calendar; they know it exists and no decision is attached
- Scores: importance 1 (money 0, deadline 2026-03-13 18:00 (7d, +85 h), blocks others False, irreversible False); time-sensitive False
- Already known: no earlier mention found since 2026-02-28
- Novelty gate: first touch

**Newsletter digest cleanup** `newsletter-cleanup` (your task list)
- State: Forty unread newsletters.
- Why HOLD UNTIL USER RAISES IT: standing do-not-nag topic: you asked not to be nagged about newsletters
- Scores: importance 0 (money 0, deadline none, blocks others False, irreversible False); time-sensitive False
- Already known: no earlier mention found since 2026-02-28
- Novelty gate: first touch

### DROP (6)

**Upcoming: Call with the Harbor & Pine finance lead** `cal:evt-1` (calendar)
- State: starts 2026-03-10 15:00
- Why DROP: no artifact, no recommendation, importance 4: a bare reminder is not a chase
- Scores: importance 4 (money 0, deadline 2026-03-10 15:00 (24h, +10 h), blocks others False, irreversible False); time-sensitive True
- Already known: no earlier mention found since 2026-02-28
- Novelty gate: first touch

**Migrate the old wiki** `old-wiki` (your task list)
- State: Open since last autumn.
- Why DROP: stale: last verified 128 d ago, no fresh evidence, no deadline in the next 7 d. A verify-first task for the agent, not a chase.
- Scores: importance 0 (money 0, deadline none, blocks others False, irreversible False); time-sensitive False
- Already known: no earlier mention found since 2026-02-28
- Novelty gate: first touch

**Cold pitch: boost your SEO in 7 days** `seo-pitch` (your task list)
- State: Unsolicited email.
- Why DROP: cold outreach pattern: not worth a chase or a prep
- Scores: importance 0 (money 0, deadline none, blocks others False, irreversible False); time-sensitive False
- Already known: no earlier mention found since 2026-02-28
- Novelty gate: first touch

**Job in flight: index-rebuild** `job:index-rebuild` (jobs)
- State: Still inside its window.
- Why DROP: the job is still inside its window and running; the job tracker owns it. Nothing to tell yet.
- Scores: importance 0 (money 0, deadline none, blocks others False, irreversible False); time-sensitive False
- Already known: no earlier mention found since 2026-02-28
- Novelty gate: first touch

**Promised later delivery** `promise:d98e2493` (conversation)
- State: 5.1 h ago: "The export is running. I'll ping you the moment it finishes."
- Why DROP: cannot verify non-delivery in any stream; a bare promise with no artifact is not a chase
- Scores: importance 0 (money 0, deadline none, blocks others False, irreversible False); time-sensitive False
- Already known: no earlier mention found since 2026-02-28
- Novelty gate: first touch

**Unanswered message from the user** `owed:s5` (conversation)
- State: they wrote 2.5 h ago and the conversation ends on their message: "also rebuild the search index with the new tokenizer settings"
- Why DROP: already being handled by job 'index-rebuild'
- Scores: importance 0 (money 0, deadline none, blocks others False, irreversible False); time-sensitive True
- Already known: no earlier mention found since 2026-02-28
- Novelty gate: first touch
