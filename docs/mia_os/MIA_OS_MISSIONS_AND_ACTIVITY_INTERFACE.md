# MIA OS: missions, projects and activity (Prompt 10 §13)

*Claude (Opus), 2026-11-17. Planning only. The model is Prompt 08's (DEC-0214).*

| Shows | Where | Exists |
|---|---|---|
| Active mission, projects, milestones | `missions.html`, `projects.html` | yes |
| A plan's steps and dependencies | `plan.html`, `steps.html` | yes |
| Runs: what's running, paused, failed | the run record (`core/runs.py`) | partial screen |
| Pending approvals | the cards; a list in Notifications | yes |
| Agents and specialists at work | `specialists.html`, the project workspace | partial |
| Her own changes and repairs | Diagnostics (Prompt 09) | yes |

**Controls**, each an action on the contract: start, pause, resume, cancel, reprioritise, reassign, inspect the plan,
approve, review what was done. The stop ("stop everything") is on the status strip.

**Real, simulated or game:** every activity carries a label: **Real** (a task in his life), **Simulated** (a Living
World, a rehearsal), **Game** (the Dungeon's quests and XP). XP may be earned by real tasks but a game mechanic is
never shown as a real obligation, and a productivity screen is never gamified unless he turns it on.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-021 | Every activity shown shall be labelled real, simulated or game. | Must | R1 | All | Partial (SIMULATED status) | T | DEC-0228 → 10 |
| REQ-DSK-022 | A running plan shall be pausable, resumable and cancellable from its screen and by voice. | Must | R1 | All | Partial (the stop) | T | DEC-0214 → 10 |
