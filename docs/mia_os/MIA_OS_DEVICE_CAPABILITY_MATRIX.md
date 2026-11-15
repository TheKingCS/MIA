# MIA OS: device capability matrix (Prompt 02 §12)

*Claude, 2026-11-15.*

*Key:*
- *● full*
- *◐ through another device or reduced*
- *○ shown only (no local processing)*
- *— not applicable*
- *✗ unavailable offline*

*This describes the target. Today's state is in the inventory. Phone ↔ PC
is real today; the glasses go through the phone (Meta's toolkit); the Pi
is later (DEC-0015).*

| Capability | PC | Phone | Glasses | Wearables | Pi / embedded | Offline |
|---|---|---|---|---|---|---|
| Talk (text) | ● | ● (own model) | ◐ via phone | ◐ | ◐ | phone and PC models work offline |
| Voice in and out | ● | ● | ● mics and speakers through the phone | ◐ | ● (Pi) | yes |
| Speaker ID | ● | ● | ◐ via phone | — | ◐ | yes (on device) |
| Heavy inference (14b) | ● | ◐ via home link | ◐ | — | — | PC only |
| Dashboard | ● | ● | ○ cards | ○ | ○ kiosk | yes (stale online parts marked) |
| Missions, Loop, Dungeon | ● | ● | ○ | ○ reminders | — | yes |
| Finances | ● | ● | ○ summary | — | — | yes; bank refresh ✗ |
| LEP discovery | ● | ◐ | — | — | — | ✗ (needs online sources) |
| LEP plans, Spontaneous Mode | ● | ● | ○ top 3 nearby | ○ | — | saved catalogue only |
| Smart Closet | ● | ● (camera for photos) | ○ outfit of the day | — | — | yes (weather stale) |
| Camera and vision | ◐ | ● | ● (glasses camera) | — | ● (greenhouse cams) | captions need a model |
| Location | — | ● | ◐ via phone | ◐ | fixed | yes |
| Homestead control | ● | ● | ○ alerts | — | ● deterministic controllers | **must** work offline locally |
| Send to MIA on a selection | ● (hotkey, MIA OS service) | ● (selection menu, share) | — | — | — | yes for local actions |
| Development council, agents | ● | ○ view | — | — | — | ✗ (cloud) |
| Backups, sync | ● | ● | — | — | ◐ | sync needs reach |
