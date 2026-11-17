# MIA OS: physical safety (Prompt 13 §20)

*Claude (Opus), 2026-11-18. Planning only. DEC-0185, DEC-0246.*

| Layer | Owns | Can't be overridden by |
|---|---|---|
| Hardware interlocks (thermal cut-outs, float switches, breakers) | the last line | anything in software |
| The safety MCU | hard limits | the node, MIA |
| The node's control loop | setpoints within limits, validated ranges | MIA |
| MIA | proposals: a setpoint, a schedule | — |

**A command MIA proposes** is validated three times: by its action's code (allowed ranges per device), by the node's
own interface (its limits), by the safety MCU (hard limits). A rejected command is recorded and said. **"Stop
everything"** never touches the greenhouse (DEC-0185): stopping a controller mid-cycle could itself be unsafe.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-033 | A command to physical equipment shall be checked against its allowed range in MIA's action, again by the device, and again by its hardware limits; a rejection shall be recorded and told. | Must | MVP | Node | Partial (node and MCU) | T: homestead scenarios | DEC-0246 → 13 |
