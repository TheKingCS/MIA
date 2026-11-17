# MIA OS: self-awareness security and integrity (Prompt 09 §19)

*Claude (Opus), 2026-11-17. Planning only. Prompt 13 designs security as a whole.*

| Threat | Control | Exists |
|---|---|---|
| She weakens her own safeguards | the protected list; the lab refuses before testing | yes |
| A change that passes tests but does harm later | automatic revert at merge; loops watched after; Zac can revert any | yes / partial |
| Fake evidence (a model claiming a test passed) | test results come from the runner, never a model's words | yes |
| A poisoned self-report | the report is assembled in code from records | yes |
| Development records leak his data | the public-repo rule; nothing personal in `work/` or commits | yes |
| Claude's pass covering a dangerous change | protected files can't be changed whatever the pass; the suite still must pass | yes |
| Inspection itself tampered with | `core/model_inspection.py` proposed for the protected list | new |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SLF-021 | Evidence that a test passed or a model was benched shall come only from the runner's own output, never from a model's report. | Must | MVP | All | Exists | T | DEC-0221 → 09 |
