# MIA OS: the multi-device strategy (Prompt 12 §2)

*Claude (Opus), 2026-11-18. Planning only.*

| Principle | Means | True today |
|---|---|---|
| One MIA | one identity, one memory, one history per person; devices are her places, not copies with their own minds | yes: the same engine, synced records, the history merged by event id |
| Different devices, different jobs | the PC thinks hard and keeps the records; the phone travels and works alone; the glasses show and listen; nodes watch and control | yes |
| Local first | every full engine answers from its own records and model with no network | yes (phone, PC) |
| Distribution where it helps | big thinking on the GPU; a node near the thing it watches | yes (level 2 link; greenhouse node) |
| No device is required but the one in his hand | losing the PC costs the big model and sync, never his records on the phone | yes |

**Order of devices** (DEC-0015, Q-66): the PC, the phone, the glasses, then the household display, the Pi 5, a
laptop and tablet, Zeta Astralis.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-001 | Every full engine (the PC, the phone, later the laptop) shall answer from its own records and model with no network. | Must | MVP | All | Exists | T: offline tests | DEC-0241 → 12 |
| REQ-DST-002 | A device being off or unreachable shall cost only what it alone provides, never another device's records. | Must | MVP | All | Exists | D | DEC-0241 → 12, 14 |
