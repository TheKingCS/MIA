# MIA OS: home and homestead devices (Prompt 12 §16; DEC-0246)

*Claude (Opus), 2026-11-18. Planning only. The node: `homestead/` (DEC-0145, DEC-0150, DEC-0185).*

| Layer | Owns | MIA's part |
|---|---|---|
| Safety MCU | hard limits (heat, water, power): acts without anyone | none; never overridden |
| The node's control loop | setpoints, schedules, sequencing | reads its state; proposes setpoint changes (DEC-0185) |
| The node's exports and live view | read-only snapshots, the dashboard | pulled on his network (`greenhouse_link`) |
| Sensors | single readings | logged to their series (`core/sensors.py`) |
| MIA | understanding, alerts, history, his questions, offers | through the gate; changes as actions |

**Rules (kept):** nothing here sends the node a command without an approved action; "stop everything" never touches
the greenhouse (DEC-0185); the node's safety never depends on MIA, the PC or the network. **Other home devices**
(lights, cameras, a smart plug) follow the same split: their own controller owns the loop; MIA reads and proposes.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-021 | A controller's safety limits shall never depend on MIA, the PC or the network. | Must | MVP | Node | Exists (the safety MCU) | T: homestead scenarios | DEC-0246 → 12 |
| REQ-DST-022 | MIA shall change a controller only through an approved action sent to its own interface, reading the result back. | Must | R1 | Node | Partial (read-only today) | T | DEC-0185, DEC-0246 → 12 |
