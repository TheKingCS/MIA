# MIA OS: hardware failure and degraded operation (Prompt 06 §19)

*Claude (Opus), 2026-11-17. Planning only. Reliability requirements: `MIA_OS_RELIABILITY_AND_DEGRADATION_REQUIREMENTS.md`
(Prompt 04); recovery: Prompt 14.*

| What fails | What MIA does | What still works | He's told |
|---|---|---|---|
| The graphics card (driver crash, removed) | the model runner restarts on Vulkan or CPU, or asks the model node | conversation (slower), everything not model-based | "I'm running on the processor; answers will be slower" |
| ROCm broken after an update | Vulkan path; the image can roll back (bootc) | everything | which path, and that a rollback is available |
| Memory pressure | systemd-oomd stops the lowest-priority service; MIA unloads models first | conversation | what was stopped |
| The drive fills | background work that writes waits; old snapshots offered for removal | reading, conversation | at 90% and 95% |
| The drive fails | the last backup (Prompt 14) | the phone's own copy of his records | immediately, through every device |
| Power cut, with a UPS | finish writes, stop model work, clean shutdown | — | on return |
| Power cut, no UPS | atomic writes leave every store whole (`atomic_write_text`); the journal shows the cut | — | on return |
| Network down | each device alone; sync later (REQ-DEV-004) | everything local | which device can't reach which |
| The model node offline | its models aren't offered; placement falls back to the PC | everything | "the larger model isn't reachable" |
| The phone lost | revoke it from the PC (REQ-DEV-002) | the PC | — |
| The glasses or their toolkit | phone and PC carry every action | everything | — |
| The homestead node | the safety MCU keeps hard limits; the greenhouse holds its last settings | the greenhouse, safely | the node is offline |
| The safety MCU | the node fails safe (heater off, vents to default) | — | an alarm, always delivered |
| Overheating | background model work waits; the kernel throttles | conversation | if it persists |

**Rule:** a failure is said in plain words with what still works, never hidden behind a generic error, and nothing
physical depends on the PC or MIA being up (REQ-HW-017, 018).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-HW-031 | Each row above shall have a test that simulates the failure and checks what keeps working and what he's told. | Must | R1 | All | Partial (homestead scenarios; atomic writes) | T | → 14 |
