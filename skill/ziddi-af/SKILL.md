---
name: ziddi-af
description: >
  Persistence loop in two halves. RELENTLESS: before telling the user something can't be done, is blocked or only they can do it, climb a ladder of different approaches and cite an attempt-log id. CHASE: go to the user first with a finished artifact or a recommended decision, triaged and never repetitive. Use when a draft reply says can't, blocked, doesn't work or only you can, when you promise later work, when a background job finishes, or when the user says ziddi, don't give up, find another way, chase me.
version: 1.0.0
triggers:
  - ziddi
  - ziddi af
  - don't give up
  - find another way
  - chase me
  - keep me posted
  - resume where you left off
user-invocable: true
disable-model-invocation: false
status: stable
side-effects: writes
---

# Ziddi AF

*Ziddi* is Hindi for stubborn. Be stubborn about the goal, never about the guardrails. The user should not have to chase their agent; the agent chases them, with the work already done. Not an alarm clock: a professional who shows up with the finished thing and one small next move.

## When to use this

Situation triggers (fire without being asked):

- You are about to write "can't", "unable to", "blocked", "doesn't work", "only you can", "needs you to do it", or "no way to".
- You just promised later work ("I'll tell you when", "will post here when", "keep you posted").
- A job or background process you started has finished or died.
- A conversation ends on the user's message with no reply.
- A scheduled tick (a morning brief, a scheduled check, a cron job) has open items for the user.

Phrases: "ziddi", "don't give up", "find another way", "chase me", "resume where you left off", "keep me posted".

**Do not use this when:** the obstacle is a gate (an approval you do not hold, a publish rule, a production guardrail, a data-loss step, a refused action). Log it as `gated` and ask the way the gate says; do not climb. Or the answer lives only in the user's head and you already checked your own records: ask once, briefly.

## Inputs

| Input | Required | If missing |
|---|---|---|
| The goal in the user's own words | yes | Use their last message verbatim. |
| `scripts/attempts.py` | for Half 1 | Without it you may not give up. |
| `ziddi.config.json` | for Half 2 | Defaults apply (UTC, quiet hours 00:00-06:00, no signal sources). Copy `examples/ziddi.example.config.json` and edit. |

## Steps

### Half 1: RELENTLESS (inside a task)

1. **Open the log before you say "can't".** `python3 scripts/attempts.py add --goal "the user's goal" --rung tool --did "what you did" --result fail --why "the real reason" --cmd "the command"` prints an id like `zid-20260310-a1b2`. Pass `--id` on every later attempt. Log failures with the real reason; "didn't work" is not a reason.
2. **Climb the ladder, in order. Distinct means a different mechanism, not the same command with new flags** (the log counts `curl -A x` then `curl -L -H y` as one mechanism):
   1. `fix-cause`: retry after fixing the diagnosed cause.
   2. `tool`: a different tool for the same job.
   3. `path`: a different API, CLI, endpoint or route.
   4. `assets`: scripts, MCP servers, credentials and integrations that already exist in your own setup. **Required.**
   5. `memory`: your notes, memory and past transcripts for a prior working path. **Required.**
   6. `web`: web, docs, source.
   7. `decompose`: solve the sub-part that is solvable; hand over only the remainder.
   8. `adjacent`: an adjacent outcome that gets most of the value.
3. **You may not call it exhausted until the log shows 4 distinct mechanisms over 3 rungs, including `assets` and `memory`** (all configurable). `attempts.py verdict <id> --outcome exhausted --ask "the ONE thing needed from the user" --recommend "what you suggest"` refuses otherwise and names the missing rung.
4. **Escalate with the receipt.** `attempts.py receipt <id>` prints what was tried, why each failed, the one thing needed, and your recommendation. Answer first, then the receipt, citing the id. `scripts/ziddi_giveup_check.py --verify --text "the draft reply"` flags any give-up that lacks a valid id.
5. **If an attempt works, close with `--outcome solved` and say what you did, not how hard it was.**

**Stop rule. Gates are never obstacles.** Do not route around any of these with a "different mechanism": an approval you do not hold, a publish or send rule, a production guardrail, a data-loss or destructive step, credentials that are not yours, spending money or premium resources without standing authority, any refused action. Log `verdict --outcome gated --gate <name>` and ask. **Budget:** about 20 minutes of wall clock per goal and no paid spend on your own. At the budget, `verdict --outcome budget-stop --ask ... --recommend ...` (it checks the clock). The user saying "keep going" extends it.

### Half 2: CHASE (outside a task)

Run `python3 scripts/ziddi_chase.py --dry-run` (add `--live` only when the user has wired delivery). Hard checks, enforced in code:

1. **Every chase carries an artifact, or a decision with a recommendation.** "I went through X, here is Y, I recommend Z, reply 1 or 2." Never "just checking in" or a bare reminder. No artifact yet: prepare it first, then chase.
2. **Triage every candidate into one of four classes and show the reason.** CHASE NOW: important, time-sensitive, not already known, not something you can do yourself, carries an artifact or recommendation. BATCH: goes in the digest (finished jobs, prep items, deadlines still far out, "I did it, done" receipts). HOLD UNTIL USER RAISES IT: parked, already known with nothing new, a standing do-not-nag topic. DROP: stale and unverified, closed, a bare reminder.
3. **If you can just do it, do it, report done, do not ask.** Reversible, in your own lane, no gate involved (a draft, a read-only check, a renewal, a fix to your own tooling). The result is a receipt in the digest, not an interrupt.
4. **Dedupe on new information only; no daily cap.** A chase is allowed only if it carries NEW information or a NEW next step versus the last touch on that item. The gate fingerprints what you would say plus the deadline tier. Same item, same fingerprint: HOLD, however long it has been. A deadline entering 48 h, 24 h or 1 h, or going 7 or 14 days overdue, counts as new information.
5. **Bite-sized, solution-first.** Break the goal into problem-to-solution steps, smallest first. The message shows ONE next action with its honest time cost ("Send me the number, 30 seconds") and one low-effort reply token. Plain literal language; no riddles, no guilt, no stacked questions. Shape: `[ACTION] title`, `State:`, `Next:`, `Reply:`. About 60 words; a long item goes as a second message.
6. **Quiet hours** (default 00:00-06:00 in your timezone) **unless the user is active** (they did something on any surface in the last 30 minutes): then act normally. Otherwise a CHASE NOW queues for the batch time and `ziddi_chase.py flush` sends it.
7. **Escalation cadence.** 1st touch: the artifact, the recommendation, the smallest step. 2nd touch: only with new information, and if the item has a pre-agreed reversible `default_action`, say what you will do and by when. 3rd touch: never a louder repeat; execute that reversible default and report done with how to undo it. No default, or the item is gated on the user: park it. Silence is never consent for a gated action.

### Wire it up yourself

Signals come from adapters you configure (`items`, `jobs`, `conversation`, `ics`, `command`); delivery from `stdout`, `file` or `webhook`. Nothing ships pointing at a real account. See `references/signals.md` and `references/delivery.md`.

| Need | Command |
|---|---|
| Log an attempt | `python3 scripts/attempts.py add --goal ... --rung ... --did ... --result fail --why ... [--cmd ...] [--id zid-...]` |
| Show / close / receipt | `attempts.py show <id>`, `verdict <id> --outcome exhausted\|solved\|gated\|budget-stop ...`, `receipt <id>`, `open` |
| Check a draft reply | `python3 scripts/ziddi_giveup_check.py --verify --text "..."` (exit 1 means flagged) |
| Dry-run the chase | `python3 scripts/ziddi_chase.py --config ziddi.config.json --dry-run --md out.md` |
| Send / flush the queue | `ziddi_chase.py --live`, `ziddi_chase.py flush --live` |
| Tests | `python3 -m unittest discover -s tests` |

## Output

Half 1: rows in `$ZIDDI_HOME/attempts.jsonl` (default `~/.ziddi/`), append-only, and a reply that cites an id. Half 2: a ranked candidate list; every candidate has its class, reason, scores, whether the user already knows, and the gate result; messages only for CHASE NOW. A dry run sends and writes nothing.

## Failure modes

- **Climbing for show.** Five renamed curls. The log dedupes by binary, and `exhausted` needs `assets` and `memory`; if you are padding, you are not solving.
- **Climbing past a gate.** A "creative workaround" for an approval is a violation, not persistence.
- **Chasing what the user already knows.** The engine reads a log of what you sent. If you deliver by other means, append those messages to `sent.jsonl` or list the log under `known_logs`.
- **A chase with no artifact.** It cannot go out. Prepare first.
- **Detector false positives.** It is tuned for precision, not recall (see README). Run the hook in observe mode before enforcing, and set `ZIDDI_OFF=1` in sessions that write status digests.
- **Attempt log with no verdicts.** `attempts.py open` lists ids with no verdict; close them.

## Safety

Writes only the attempt log, the gate state, the queue, the sent log and (optionally) an outbox file, all under `$ZIDDI_HOME`. The chase engine is dry-run unless you pass `--live` and have chosen a delivery adapter. Never edits your agent's settings, hooks or schedules. To undo: delete `$ZIDDI_HOME`; attempts are evidence, not state.
