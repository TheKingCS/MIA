# MIA OS: self-modification and the code lifecycle (Prompt 09 §14)

*Claude (Opus), 2026-11-17. Planning only. Build infrastructure is Prompt 15's.*

| Stage | What happens | Evidence kept | Exists |
|---|---|---|---|
| Proposed | a finding, a gap or a lesson becomes a task | the task, its source | yes (`work/tasks`) |
| Written | in a lab worktree, test first | the branch | yes |
| Checked | protected list; full suite before and after; documentation tests | the run | yes |
| Inspected | Claude reads the diff and the tests (read-only) | the verdict | yes (DEC-0200) |
| Merged | into the running copy; the suite again | the commit | yes |
| Watched | the next days' Fix-It Log and loops for its area | the loops | partial |
| Reverted | automatically on a new failure at merge; by him at any time | the revert commit | yes |
| Released to MIA OS | as part of the image (Prompt 14) | the image version | planned |

Every change is a commit with its reason, linked to its task and knowledge entry, in the public repository (so never
his personal data).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SLF-016 | Every self-made change shall be traceable from the finding or task that caused it to the commit, its tests, its inspection and its effect on the loops after. | Should | R1 | PC | Partial | T | DEC-0225 → 09, 15 |
