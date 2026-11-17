# MIA OS: keeping failures contained (Prompt 14)

*Claude (Opus), 2026-11-18. Planning only.*

| Failure | Contained by | Exists |
|---|---|---|
| A job throws | the scheduler: recorded, backed off, the others run (REQ-REL-003, 012) | yes |
| A store's file is damaged | that store starts empty, the file kept aside, he's told (REQ-REL-006) | yes |
| An app's code fails | the module manager skips it; the rest load | yes |
| The model server hangs | timeouts; self-repair; screens unaffected | yes |
| The runtime crashes | systemd restarts it, at most three times in a row, then says so (REQ-REL-004) | partial |
| The shell crashes | restarted; his other windows untouched (REQ-DSK-031) | planned |
| Memory pressure | systemd-oomd ends the least important first; models unloaded before the shell | planned |
| A bad self-change | the lab reverts it | yes |
| A runaway resource | each unit in its own slice with limits (CPU weight, memory high) | planned |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-019 | Each of MIA's units shall run in its own slice with memory and CPU limits, so one can't starve the desktop or the others. | Should | R1 | PC | Planned | T | DEC-0256, DEC-0195 → 14 |
