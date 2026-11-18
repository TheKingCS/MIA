# MIA OS: gates (Prompt 16; DEC-0274)

> **Prompt 17 (2026-11-18):** superseded where it differs by `MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md`, `MIA_OS_FINAL_MVP_AND_RELEASE_DEFINITION.md` and `MIA_OS_FINAL_MIGRATION_AND_DATA_CONTINUITY_PLAN.md`. Corrections: proof of concept 2's headless boot, update and rollback **passed** on 2026-11-16 (GitHub run 43872077107), so "boot to do" is wrong; the login manager is Plasma Login Manager, not SDDM; DEC-0269, 0270 and 0272 are approved (`docs/DECISIONS.md`).

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
