# MIA OS: what he sees when the PC starts (Prompt 14)

*Claude (Opus), 2026-11-18. Planning only.*

| Moment | He sees | Exists |
|---|---|---|
| Power on | the maker's logo, then a quiet MIA boot splash (Plymouth, the theme's colours) | planned |
| Disk unlock | nothing (the TPM unlocks it); his recovery key only if the TPM refuses | planned |
| Login | SDDM: MIA (default) and Plasma | planned |
| MIA's session | the shell at once with "Starting up…"; Home fills in as the runtime is ready | partial (the splash and startup sound on Windows) |
| Ready | her orb settles; the startup sound if he chose one | yes (`core/boot_sound.py`) |
| Something wrong | a plain line: "Voice isn't ready: the speech model is missing. Fix it in Diagnostics." | partial (`core/system_check.py`) |
| First ever start | the setup wizard: his account, the data key's recovery key to keep, his devices | yes (Windows) |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-016 | From login to MIA's Home showing his day shall take under 10 seconds, with anything not ready said in one plain line. | Must | MVP | PC | Partial | M | DEC-0255, REQ-PER-001 → 14 |
