# Delivery: how a chase leaves the building

`ziddi_chase.py` is a dry run until you pass `--live`. `--live` sends every CHASE NOW through the adapter in `"delivery"`, records it in the gate (so it is never said twice) and appends it to `sent.jsonl`. During quiet hours with the user inactive it queues instead, and `ziddi_chase.py flush --live` sends the queue once it is allowed. One failed send is reported once and never retried blind: a failure means a wrong address, so fix the address.

| Adapter | Config | What it does |
|---|---|---|
| `stdout` (default) | `{"adapter": "stdout"}` | prints the message. Good for piping into anything. |
| `file` | `{"adapter": "file", "path": "outbox.jsonl"}` | appends `{ts, key, text}` rows. Another process (or you) picks them up. |
| `webhook` | `{"adapter": "webhook", "webhook_url_env": "ZIDDI_WEBHOOK_URL", "payload": "slack"}` | POSTs JSON to the URL in that environment variable. `payload` is `slack` (`{"text": ...}`), `discord` (`{"content": ...}`) or `generic` (`{"text": ..., "key": ...}`). |

The URL is read from the environment so it never sits in a file you might commit.

## Wiring recipes (you do these yourself; nothing here is pre-connected)

- **Slack**: create an incoming webhook for a channel you own, `export ZIDDI_WEBHOOK_URL=...`, set `"payload": "slack"`.
- **Discord**: channel settings, Integrations, Webhooks, copy the URL, `"payload": "discord"`.
- **WhatsApp, Telegram, SMS, any gateway with an HTTP API**: use `webhook` with `generic` and a small relay that maps `{"text": ...}` to your gateway's send call; or use the `file` adapter and let your agent's own send tool read the outbox.
- **Email**: the `file` adapter plus a 10-line script using `smtplib`, or a mail-to-webhook service. Email is the slowest surface; keep chases for it rare.

Rule of thumb: send chases to a place you read on your phone, not to the chat where you do deep work. A chase is an interrupt; give it its own lane.

## The batch

BATCH items are the digest. Print them into whatever brief you already read: `ziddi_chase.py --md digest.md` and include the BATCH section. No second digest route is needed.
