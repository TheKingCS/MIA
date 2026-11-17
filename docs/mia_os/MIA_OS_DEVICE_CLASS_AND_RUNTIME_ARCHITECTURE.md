# MIA OS: device classes and their runtimes (Prompt 12 §4, §5)

*Claude (Opus), 2026-11-18. Planning only. Hardware: Prompt 06 (DEC-0201 to 0205).*

| Class | Device | Runtime | Keeps records | Models | Interface | Works alone |
|---|---|---|---|---|---|---|
| **Hub** | the PC (Ryzen 9800X3D, RX 7900 XTX) | the full engine as a service (MIA OS) or the desktop app (Windows) | yes, of record | big (Ollama, GPU) | desktop shell | yes |
| **Full engine** | the phone; later the laptop | the full engine (Chaquopy on Android) | a synced copy | small (llama.cpp on the phone) | phone screens | yes |
| **Endpoint** | the glasses; the household display; Zeta Astralis | none of its own: shows and listens for an engine | none | none | cards, ambient layout, compact layout | no |
| **Node** | the Pi 5 (+ AI HAT+ 2) | the Core edition (`device_profile`), or a homestead node | its own (expeditions, readings) | small (the HAT) | kiosk (cage) or none | yes |
| **Controller** | the greenhouse's safety MCU, ESP32s | their own firmware and loops | none of MIA's | none | none | yes, by design |
| **Sensor** | anything that posts a number | a single-purpose key | none | none | none | n/a |

**One codebase:** hub, full engines and nodes run the same engine with a profile (`device_profile`: Home or Core,
plus the phone build); what differs is what's turned on (models, voice, the desktop shell, the schedule's jobs).
**Endpoints run no engine**: they render an engine's web screens or the glasses' cards and pass voice through.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-003 | Hub, full engines and nodes shall run one codebase, told apart by profile, never by forks. | Must | MVP | All | Exists | R | DEC-0241 → 12, 15 |
| REQ-DST-004 | An endpoint shall keep no records of its own beyond what it shows now. | Must | R1 | Endpoint | Exists (glasses) | T | DEC-0241 → 12, 13 |
