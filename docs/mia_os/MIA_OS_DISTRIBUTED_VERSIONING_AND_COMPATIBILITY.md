# MIA OS: versions across devices (Prompt 12 §19)

*Claude (Opus), 2026-11-18. Planning only. Updates themselves: Prompt 14.*

| Concern | Rule |
|---|---|
| Versions | each engine reports its version (commit) when it pairs and on each sync |
| Data | store files carry no schema version today; changes are additive (new fields default), which sync's merge tolerates |
| API | `/api/*` additions only; a removal waits until every paired device runs a version without it |
| Too old | the hub tells a device "update MIA on this phone" when its version is older than the oldest the hub accepts, and keeps answering what it safely can |
| The phone app | built and installed by him (T-0012); its version shown in Sign-ins |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-026 | Each device shall report its version; the hub shall say plainly when a device is too old and keep serving it what's safe. | Should | R1 | All | New | T | DEC-0244 → 12, 14 |
