# MIA OS: execution verification (Prompt 08 §20; DEC-0218)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. Done means read back

| Reach | Verified by | Exists |
|---|---|---|
| Records | re-read the store after `execute` and compare with what `describe` promised | **new** (stores are written atomically; nothing re-reads) |
| The web | the page's state after the step (her browser reads it), the order number on a receipt | partial |
| A device | the device's own report (the node's reading after a setting) | partial (greenhouse) |
| The system | the helper's result and the system's own state (a package version, a service active) | planned |
| Outside (an email sent by him) | the mail system's sent copy | yes (drafts only; he sends) |

**A model saying "done" is never evidence.** A run's step is `done` only after its check passes; a failed check marks
it `failed` with what was found, and offers undo or compensation.

## 2. A plan's success

A goal's success criteria are checked by code when they're records (heater tested: a reading logged; needs covered:
the requirements' status); otherwise MIA asks him.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-030 | After executing an action, code shall read its effect back and mark the step done only when it matches what was promised. | Must | R1 | All | New | T: a store that silently fails is caught | DEC-0218 → 08 |
| REQ-AGT-031 | A model's report of success shall never mark a step done. | Must | MVP | All | Exists (steps marked by code) | T | DEC-0218 → 08 |
