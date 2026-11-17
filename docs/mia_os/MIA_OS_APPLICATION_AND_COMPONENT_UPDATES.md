# MIA OS: updating apps and parts (Prompt 14)

*Claude (Opus), 2026-11-18. Planning only. App distribution: `MIA_OS_APPLICATION_DISTRIBUTION_AND_UPDATES.md`.*

| Part | Updated by | Rollback |
|---|---|---|
| MIA's code and apps | the image (DEC-0257) | the previous deployment |
| Her own changes (the lab) | merge on Claude's pass, suite, revert | git revert; the daily summary's Undo |
| Models | `ollama pull`, benched and inspected before specialists use a new one | keep the old one until the new passes |
| Voice models | downloaded by the setup script | the previous file kept |
| Flatpak apps | Flatpak | `flatpak update --commit` |
| The phone app | built and installed by him | the previous APK |
| The greenhouse node | its own image and update | its own |
| Firmware (ESP32s) | flashed on his yes | the previous build kept |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-025 | A new model shall replace an old one for a specialist only after it passes the bench and Claude's inspection; the old one stays until then. | Must | R1 | PC | Partial (bench, inspection) | T | DEC-0200, DEC-0257 → 14 |
