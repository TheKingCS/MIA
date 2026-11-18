# MIA OS: environments (Prompt 15)

*Claude (Opus), 2026-11-18. Planning only.*

| Environment | For | Data |
|---|---|---|
| His PC (Windows today) | real use, real models, the benches | his own |
| The lab's worktrees | her changes | none of his (by construction) |
| Scratch worktrees | each commit's checks | none |
| GitHub's runners (Ubuntu, Windows) | CI | fixtures only |
| A VM (QEMU, in CI) | the OS image | fixtures only |
| A Fedora USB stick | PoC 1 on his real GPU | none written |
| The laptop (later) | a second engine to test sync | his own, synced |
| `MIA_HOME` | pointing MIA at a test data folder | fixtures |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-027 | No test or development environment shall read or write his real data except his own MIA. | Must | MVP | All | Exists (MIA_HOME, fixtures) | T | DEC-0262 → 15, 13 |
