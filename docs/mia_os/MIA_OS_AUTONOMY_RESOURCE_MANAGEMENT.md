# MIA OS: autonomy performance, cost and resources (Prompt 08 §23)

*Claude (Opus), 2026-11-17. Planning only. Hardware coordination: DEC-0204.*

| Resource | Rule | Exists |
|---|---|---|
| The GPU | one model job at a time; conversation first, then specialists, the Workroom, background | proposed (DEC-0204) |
| Background work | homeostasis eases off when busy, on battery, offline, low on disk | yes |
| Model calls in a team | a budget approved up front | T3 |
| Cloud usage (development) | the council floor's budgets; members resting at a limit skipped | yes |
| Disk | warnings before 10% free (REQ-HW-013) | partial |
| His attention | the gate's learned pace; quiet hours (Q-75) | yes / partial |

**Cost is shown before it's spent:** a team's calls, a long job's time, a download's size.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-034 | Work that will take long or spend a budget shall say its expected cost before starting. | Should | R1 | All | Partial | T | DEC-0204 → 08 |
