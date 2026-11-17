# MIA OS: autonomy failure, recovery and rollback (Prompt 08 §21)

*Claude (Opus), 2026-11-17. Planning only.*

| Failure | What happens | Exists |
|---|---|---|
| A step's check fails | step failed with what was found; dependents wait; undo or compensation offered | partial (failed steps; retry) |
| A step errors | logged, failed, the plan continues where it can; one broken step never takes the plan | yes (`step_plans.do`) |
| A restart mid-run | the run record marks it stopped where it was; "run it again from step N" | yes (runs recovery) |
| A stale approval | proposals expire in a day; a plan's card is re-checked before it runs | yes |
| A partial multi-store change | each store writes atomically; a plan's steps are separate changes, each undoable | yes |
| A job failing repeatedly | backoff (twice, four times, up to six hours) and a notice | yes (homeostasis) |
| A device doesn't answer | the step waits with a timeout, then asks him | partial |

**Rollback:** newest first, whole or not at all, only where nothing changed since (`change_history.undo`). Irreversible
steps have no rollback by definition; that's why they ask first.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AGT-032 | A failed step shall stop its dependents and offer undo or compensation for what it did. | Must | R1 | All | Partial | T | DEC-0214 → 08 |
