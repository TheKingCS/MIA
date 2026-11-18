# MIA OS: milestones (Prompt 16)

*Claude (Opus), 2026-11-18. Planning only. Gates: `MIA_OS_MILESTONE_ACCEPTANCE_CRITERIA.md`.*

| # | Milestone | Stage | Depends on |
|---|---|---|---|
| M0 | The approved backlog built on Windows (rolling) | 0 | — |
| M1 | The GPU proven under Linux on his PC (PoC 1) | 1 | a USB stick |
| M2 | The image boots in a VM: SDDM, the runtime at core ready, the suite passes inside | 2 | PoC 2 |
| M3 | MIA's session under KWin, Plasma beside it, safe mode (PoC 3) | 2 | M2 |
| M4 | Updates and rollback in the VM; the helper's first operations (PoC 5); Secure Boot and the TPM-unlocked disk | 2 | M2 |
| M5 | Signed images published; the phone app signed from secrets | 2 | M4; Zac's key |
| M6 | MIA OS installed on his 4 TB drive, his data moved, counts matched | 3 | M1, M3, M4; the drive |
| M7 | **The MVP**: a week as his main system, nothing lost, MVP gates passed | 3 | M6 |
| M8 | R1: recall complete, workspaces, the UAL, cross-app plans, the household display on the TV, the laptop | 4 | M7 |
| M9 | Beyond: Zeta Astralis, a model node, more devices | 5 | M8 |
