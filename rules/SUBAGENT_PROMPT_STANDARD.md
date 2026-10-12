# Sub-agent prompt standard (with the ziddi clause)

A sub-agent starts with no context and dies when its parent turn ends, so its prompt has to carry everything, including the rule that stops it from handing back a lazy "can't". Use five parts, in this order. Even a short task benefits from the first and third.

1. **Context.** What this is and why it matters, in two or three sentences.
2. **Relevance.** The exact files, data, prior work and prior failures to read first. Point at traces of earlier attempts instead of re-explaining.
3. **Instruction.** The steps, in order, with exact commands where you know them. Say what "done" looks like as a pass/fail check, not an adjective ("a stranger cannot tell the render from the original photo", not "high quality").
4. **Constraints.** What not to do, limits, safety rails. Always include the ziddi clause below.
5. **Demonstration.** One compact example of a ten-out-of-ten answer (mandatory for high-stakes tasks).

Also always inject: a voice ("pragmatic senior engineer", never "helpful assistant"), the output format and a word budget, and the sentence "end with one key principle".

## The ziddi clause (paste into the Constraints of every task)

> Before you return "can't", "blocked", "doesn't work" or "only <person> can", log your attempts (what you tried, why each failed) and cite the attempt-log id. Try at least four genuinely different mechanisms across at least three rungs: a different tool; a different API, CLI or route; scripts, MCP servers and credentials that already exist in your setup; notes, memory and past transcripts; docs; solve the solvable sub-part; an adjacent outcome. Approvals, publish and send rules, production guardrails, data-loss steps and refused actions are never obstacles to route around: name the gate and report it. When you finish, report what you did, not that it was hard.

## Rules for the parent

- A sub-agent's "done" is not done: verify the declared artifact exists and is newer than the dispatch before you report to the user.
- A builder never grades its own work: for anything substantial, a second fresh-context agent checks the real output against the pass/fail bar.
- If the work takes longer than a few minutes, it does not run as a child of a chat turn (it dies with the turn): put it on a durable runner with a declared artifact and a check that reads it.
