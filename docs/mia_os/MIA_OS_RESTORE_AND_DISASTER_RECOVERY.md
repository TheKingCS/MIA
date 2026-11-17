# MIA OS: restore and disaster recovery (Prompt 14)

*Claude (Opus), 2026-11-18. Planning only.*

| Disaster | Recovery | Time |
|---|---|---|
| A store damaged | undo, `.prev`, a snapshot, last night's backup | minutes |
| A bad update | the previous deployment | one restart |
| The disk dies | a new disk: install MIA OS, restore the latest backup (off-PC copy), enter the recovery key | about 2 hours |
| The PC is lost or destroyed | a new PC as above; or the phone's synced copy fills it | about 2 hours |
| The phone is lost | unlink; a new phone paired and synced | an hour |
| Every copy lost | — | (why two places) |

**The restore drill** (Q-98): monthly, the latest backup restored into a scratch folder, every store opened, counts
compared with the live data, the result in Diagnostics, the scratch folder deleted.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-029 | A monthly drill shall restore the latest backup into a scratch folder, open every store and compare counts, and report the result. | Should | R1 | PC | New | T | DEC-0259 (Q-98), REQ-REL-007 → 14 |
| REQ-REL-030 | A new PC shall be running his MIA with his data within two hours, following a written procedure. | Should | R1 | PC | Partial | D | DEC-0261 → 14 |
