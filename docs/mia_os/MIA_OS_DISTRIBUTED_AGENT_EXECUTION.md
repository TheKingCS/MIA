# MIA OS: agents and runs across devices (Prompt 12 §15)

*Claude (Opus), 2026-11-18. Planning only. The task model: DEC-0214; agents: DEC-0219.*

**A run belongs to one engine**: the one that started it keeps its record (`core/runs.py`), its steps and its stop.
Another device sees it through sync and can ask the owning engine to pause or stop it.

**Steps that need another device** are actions addressed to it: "water zone 2" is an action proposed on the PC,
sent to the greenhouse node's own interface (DEC-0246), its result read back (DEC-0218). The run waits for the
answer; if the node doesn't answer, the step fails plainly.

The prompt's example, as it would run:

| Step | Who |
|---|---|
| He asks for greenhouse monitoring | Talk on any device |
| The Pi collects readings | the homestead node, by itself |
| Thresholds evaluated | the node's control loop (deterministic) |
| MIA interprets | the PC's engine, from the node's snapshot |
| A workflow prepares an action | the PC, an action card (or a standing grant he gave) |
| The controller executes | the node, through its own API and safety checks |
| MIA reports | read back from the node; told on the device he's using |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-019 | A run shall be owned by the engine that started it; any of his devices may pause or stop it through that engine. | Should | R1 | All | Partial (one engine) | T | DEC-0214, DEC-0241 → 12 |
| REQ-DST-020 | A step carried out by another device shall be an action addressed to it, its effect read back before it counts as done. | Must | R1 | All | New | T | DEC-0218, DEC-0246 → 12 |
