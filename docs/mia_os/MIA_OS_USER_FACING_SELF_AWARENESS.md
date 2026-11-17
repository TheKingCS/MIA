# MIA OS: what he sees and asks (Prompt 09 §17)

*Claude (Opus), 2026-11-17. Planning only. The screens are Prompt 10's.*

| He asks | She answers from | Exists |
|---|---|---|
| "What can you do?" | the registry, by area, with what's planned said as planned | yes (capabilities) |
| "What isn't working?" | states malfunctioning, degraded, unavailable, with evidence and time | yes (status summary) |
| "Why didn't that work?" | the Fix-It Log entry and the trace | partial |
| "Which model are you using?" | the model registry | yes |
| "What did you change in yourself this week?" | merges, with their reason, tests and inspection | partial (self-report) |
| "What are you learning?" | Night School's report card | yes |
| "What can't you change about yourself?" | the protected list, in words | new (Q-78) |

**The information a status screen must expose** (for Prompt 10): each capability's state, evidence and date; what's
degraded and why; the last self-changes; what's being worked on; the protected list.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SLF-019 | MIA shall answer what she changed in herself recently, each change with its reason, tests and inspection, and how to undo it. | Should | R1 | All | Partial | T | DEC-0225 → 09, 10 |
