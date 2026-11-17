# MIA OS: autonomy observability and audit (Prompt 08 §22)

*Claude (Opus), 2026-11-17. Planning only.*

| Record | Holds | Exists |
|---|---|---|
| The action record | every proposal: who, what, when, decision, result | yes |
| The change history | before-states, 30 days, undo by time | yes |
| The run record | every run's steps, where it is, why it ended | yes |
| The grant log | each decision the grant check made (held, allowed) | yes |
| The gate's log | every unprompted message's decision | yes |
| Life events | the history of his records | yes |
| The turn trace | how each answer was reached | yes |
| Agent Activity | running, done by MIA, held back, made, the team | yes (the card) |

**Audit questions MIA answers from these:** "what did you do today?", "what did you do to the greenhouse?", "why did
you hold that message?", "what's running?", "what can you do on your own?". Records stay on his devices; the public
repository never holds them.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-033 | Every consequential action shall be recorded with who proposed it, who approved it, what it did and how to undo it. | Must | MVP | All | Exists | T | DEC-0213 → 08 |
