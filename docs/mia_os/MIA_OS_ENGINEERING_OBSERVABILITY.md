# MIA OS: seeing how engineering is going (Prompt 15)

*Claude (Opus), 2026-11-18. Planning only.*

| Signal | Where |
|---|---|
| CI results per push | GitHub Actions; `tools.ci_failures` reads a failed run's report |
| Suite size and time | the suite's summary; tracked per commit |
| Documentation coverage | the atlas's counts; the baseline only goes down |
| Tasks and who's on them | the dev board (`web/dev.html`, `tools.work`) |
| Her progress | Night School's report card, the ledger |
| Models' quality | the benches, inspections |
| Dependencies | the weekly OSV report |
| Requirements | the matrix: how many exist, partial, planned, new |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-029 | A failed CI run on master shall reach the next session's attention (the dev board or NEXT_SESSION), with which tests failed. | Should | R1 | All | Partial (`tools.ci_failures`) | T | DEC-0264 → 15 |
