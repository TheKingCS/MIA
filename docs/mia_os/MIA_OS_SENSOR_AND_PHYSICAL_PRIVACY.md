# MIA OS: microphones, cameras, sensors (Prompt 13 §18)

*Claude (Opus), 2026-11-18. Planning only.*

| Sensor | When on | Shown | Kept |
|---|---|---|---|
| Microphone (PC, phone) | while he holds or taps to talk; no wake word yet (Q-81) | the orb listening; the OS's indicator | the words, as his message; never the audio |
| Glasses camera | on his press ("what am I looking at?") | the glasses' own indicator light | the photo only if he keeps it |
| Phone camera (Look) | on his press | the app | as above |
| Security cameras | always, on the home network, his own | their app | on the PC only, never synced |
| Location | Places only when he switched it on | Settings | in his folder |
| What he's working on | while noting is on | the sidebar's line | 7 days, sealed |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-031 | No microphone or camera shall run without his press or a setting he turned on, and each shall show when it's on. | Must | MVP | All | Exists | T | DEC-0251 → 13 |
