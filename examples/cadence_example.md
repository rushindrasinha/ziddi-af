# The escalation cadence, on a fictional item

Item: pick a dentist slot before the clinic releases it at 20:00. Pre-agreed default: book the 09:00 slot tomorrow (free to cancel until 18:00 tomorrow). Same engine, four runs, delivery by the `file` adapter in a temporary folder.

| Run at | What the engine did with `dentist-slot` | Why |
|---|---|---|
| 2026-03-10 05:10 | CHASE NOW | Quiet hours, but the user messaged 20 minutes ago, so a chase goes out. Touch 1. |
| 2026-03-10 05:40 | HOLD UNTIL USER RAISES IT | 30 minutes later, nothing new. Held. |
| 2026-03-10 19:10 | CHASE NOW | Under an hour to the deadline: new information. Touch 2 announces the pre-agreed default. |
| 2026-03-10 20:30 | BATCH (digest): EXECUTE DEFAULT: book the 09:00 slot (free to cancel until 18:00 tomorrow) | Deadline passed after two touches. Touch 3 is not a louder repeat: the reversible default is carried out and reported. |

Message sent at 2026-03-10 05:10:

```text
[ACTION] Pick the dentist slot
State: Two slots left for tomorrow; the clinic holds them until 20:00 tonight.
Next: Tell me 'yes' or 'other'
Reply: yes / other
```

Message sent at 2026-03-10 19:10:

```text
[ACTION] Pick the dentist slot
State: Two slots left for tomorrow; the clinic holds them until 20:00 tonight.
Next: Tell me 'yes' or 'other'
If I don't hear by Tue 19:30, I will book the 09:00 slot (free to cancel until 18:00 tomorrow). Reply 'hold' to stop it.
Reply: yes / other
```

A gated item (`waiting_on_user`) never gets a default: with no default, the third touch is held instead of repeated. Silence is not consent.
