# MIA OS: testing reliability by breaking things (Prompt 14)

*Claude (Opus), 2026-11-18. Planning only.*

| Test | How | State |
|---|---|---|
| A store's file damaged | the suite writes garbage, checks the store starts empty and he's told | built |
| A job failing | the scheduler tests | built |
| Atomic writes under interruption | the atomic write tests | built |
| Kill the runtime four times | systemd restarts three, then stops and says so | PoC |
| Pull the power mid-write | in a VM | PoC |
| A bad update | an image that fails its health check → rolled back | PoC 2 |
| Restore drill | monthly, by code | to build |
| Network gone, the model gone | the suite runs without them (REQ-REL-001, 002) | built |
| Her own bad change | the lab's revert tests | built |
| A half-finished merge on start | to build (REQ-REL-021) | new |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-037 | Failure simulations (killed runtime, power cut mid-write, failed update) shall run in a virtual machine before each MIA OS release. | Should | R1 | PC | New | D | DEC-0256, DEC-0257 → 14, 15 |
