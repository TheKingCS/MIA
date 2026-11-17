# MIA OS: device support matrix (Prompt 12 §23)

*Claude (Opus), 2026-11-18. Planning only. Hardware detail: `MIA_OS_DEVICE_CAPABILITY_MATRIX.md` (Prompt 06).*

| Device | Class | OS | Runtime | Models | Voice | Camera | State |
|---|---|---|---|---|---|---|---|
| His PC (Ryzen 7 9800X3D, RX 7900 XTX 24 GB, 32 GB) | hub | Windows 11 now; MIA OS (Fedora KDE) | the desktop app; the service on MIA OS | qwen2.5 14B, 32B, mistral-small 24B, gpt-oss 20B, qwen2.5-VL 7B | Vosk, Piper | none | **supported** |
| His Android phone | full engine | Android | the phone app (Chaquopy) | a small llama.cpp model | the phone's | yes | **supported** |
| Meta Ray-Ban Display glasses | endpoint | Meta's | through the phone (DAT) | none | through the phone | yes (photo) | **supported** (view, voice, camera) |
| Raspberry Pi 5 + AI HAT+ 2 | node | Raspberry Pi OS / MIA OS (cage) | the Core edition | small (the HAT) | possible | possible | **planned** (Q-87) |
| The greenhouse node | node | Pi (homestead image) | `homestead/` | none | none | none | **supported** (read-only to MIA) |
| ESP32 sensors and controllers | sensor / controller | firmware | their own | none | none | none | **supported** (sensors) |
| Household display | endpoint | a tablet or small screen | an engine's web screens, household key | none | through an engine | optional | **planned** (Q-82) |
| Laptop | full engine | MIA OS or Windows | the full engine | small or none | yes | yes | **planned** (Q-66, Q-89) |
| Tablet | endpoint or full engine | Android | the phone app | small | yes | yes | **planned** (Q-66) |
| Zeta Astralis | endpoint | an old Android or the Pi 5 (Q-86) | the phone app compact layout, or web screens on the Pi | none | through its host | none | **prototype** |
| Spatial headset | endpoint | — | WebXR | none | — | — | **future** |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-032 | Each device class shall have a stated support level (supported, planned, prototype, future), and nothing shall depend on a device that isn't supported yet. | Must | MVP | All | Exists (this matrix) | R | DEC-0205, DEC-0241 → 12 |
