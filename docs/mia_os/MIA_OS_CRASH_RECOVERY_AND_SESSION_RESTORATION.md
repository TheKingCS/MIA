# MIA OS: crash recovery and picking up where he was (Prompt 14)

*Claude (Opus), 2026-11-18. Planning only.*

| After a crash or power cut | Comes back as | Exists |
|---|---|---|
| His records | exactly as last written (atomic writes) | yes |
| A half-typed message, scroll, open Talk | where they were, per page | yes (the shell keeps them) |
| Pending approval cards | within their day | yes (REQ-REL-013) |
| Runs in progress | stopped, marked "interrupted", offered to resume | partial |
| Taught-skill runs waiting | where they were | yes |
| Windows and workspaces | KWin's session restore; MIA's screens reopen | planned |
| A merge of her code mid-way | aborted on start if git says a merge or revert is in progress | to add |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-020 | After a crash, a run that was in progress shall be marked interrupted and offered to resume, never re-run silently. | Should | R1 | All | Partial | T | DEC-0214, REQ-REL-013 → 14 |
| REQ-REL-021 | On start, a merge or revert of her code left half-way shall be aborted before anything loads. | Must | R1 | PC | New | T | DEC-0225 → 14 |
