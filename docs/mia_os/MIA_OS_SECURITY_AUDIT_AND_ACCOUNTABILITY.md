# MIA OS: audit and accountability (Prompt 13 §21; DEC-0254)

*Claude (Opus), 2026-11-18. Planning only.*

| Record | Holds | Exists |
|---|---|---|
| The security log | sign-ins, devices, wrong passwords, waits, account changes, links; append-only | yes |
| The action record and change history | every change, who approved it, when, its undo | yes |
| The history (`life_events.jsonl`) | meaningful changes, never rewritten | yes |
| The communication log | every message offered, what the gate decided and why | yes |
| The run record | each multi-step run, its steps | yes |
| Grants | given, used, taken back | yes |
| Her own changes | merges, Claude's verdicts, reverts | yes |

**Tamper-evident (to add):** each security-log line carries a hash of the line before it, so a removed or altered
line shows; the head hash is copied to the phone on sync, so one device can't quietly rewrite both. **Never
recorded:** secrets, private-mode turns.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-034 | The security log shall be hash-chained and its head copied to another of his devices, so an altered or removed line is detected. | Should | R1 | All | New | T | DEC-0254 → 13 |
