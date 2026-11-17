# MIA OS: devices' reliability (Prompt 14)

*Claude (Opus), 2026-11-18. Planning only. Devices: Prompt 12.*

| Device | If it fails | Recovers by |
|---|---|---|
| The PC | the phone works alone | restart; restore |
| The phone | the PC works; the glasses wait | a new phone paired and synced |
| The glasses | the phone works | — |
| The household display (Pi on the TV) | nothing else affected | it restarts its kiosk by itself (systemd); reflashed from the image |
| The greenhouse node | its own loop and safety continue | its own recovery |
| A sensor | marked late | reflash or replace |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-033 | The household display shall restart its screen by itself after a crash or power cut, with no keyboard needed. | Should | R1 | Display | Planned | D | DEC-0256 → 14, 12 |
