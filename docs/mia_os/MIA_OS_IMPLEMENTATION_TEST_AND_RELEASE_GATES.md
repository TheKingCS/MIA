# MIA OS: gates (Prompt 16; DEC-0274)

*Claude (Opus), 2026-11-18.*

| Gate | Checked by | Passed by |
|---|---|---|
| Every commit | the full suite; docs current | the suite |
| Every push | CI on Linux and Windows | CI |
| A work package | its tests; its requirements' statuses updated in the matrix | Claude, reviewed |
| A milestone | its acceptance criteria (tests, a VM run, a demonstration on his devices) | **Zac** |
| A release | signed, booted in the VM, notes written | **Zac** (monthly, Q-101) |
| The MVP | every Must · MVP requirement passing; the scenarios; a week of use; counts matched | **Zac** |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-IMP-004 | Each milestone shall be passed only by Zac, against its written criteria, with the evidence linked. | Must | MVP | All | New | R | DEC-0274 → 16 |
