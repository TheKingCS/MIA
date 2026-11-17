# MIA OS: backups (Prompt 14; DEC-0259)

*Claude (Opus), 2026-11-18. Planning only. Protection rules: Prompt 13 (REQ-SEC-037).*

| Copy | What | Where | When | Exists |
|---|---|---|---|---|
| 1. The live data | everything | the PC | — | yes |
| 2. Nightly backup | his data and settings, encrypted with his passphrase | the PC's own disk | every night | yes |
| 3. Off the PC | the nightly backup, copied | an external drive he plugs in, or another of his machines (Q-96) | when it's there | new |
| 4. The phone | his records (sync) | the phone | when linked | yes |

**Not backed up:** models (re-downloaded), caches, derived indexes (rebuilt), the OS (in the image). **Kept:** 7
nightly, 4 weekly, 6 monthly.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-028 | Each nightly backup shall also be copied off the PC when a second place is available, with 7 nightly, 4 weekly and 6 monthly kept. | Should | R1 | PC | New | T | DEC-0259 (Q-96) → 14 |
