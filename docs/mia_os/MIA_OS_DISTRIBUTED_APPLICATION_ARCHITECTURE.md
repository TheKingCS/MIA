# MIA OS: apps across devices (Prompt 12 §13)

*Claude (Opus), 2026-11-18. Planning only. Per-app device support: the manifest's `runtime.devices` (pc, phone,
glasses, voice) and the parity table (DEC-0125).*

| An app's part | Runs where |
|---|---|
| Its records and actions | every full engine (the same code) |
| Its screens | wherever an engine shows them: the desktop, the phone, the household display, Zeta Astralis |
| Its glasses card | the phone, for the glasses |
| Its heavy work (an export, a render, a model job) | the hub, queued (DEC-0204); the phone asks and is told when it's ready |
| Its device-bound parts (cameras on the PC, the phone's location) | the device that has them |

**Manifests gain** `runtime.devices` entries for `display` (the household display) and `wearable` (Zeta Astralis),
decided per app like the glasses today. An app with a PC-only part says so on other devices ("open it on the PC").

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-017 | Every app's manifest shall say how it runs on each device class, including the household display and wearables, and parity shall measure it. | Should | R1 | All | Partial (pc, phone, glasses, voice) | T: parity | DEC-0125, DEC-0241 → 12 |
