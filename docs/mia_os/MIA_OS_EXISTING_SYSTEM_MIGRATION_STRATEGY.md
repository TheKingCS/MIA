# MIA OS: moving from Windows (Prompt 16; DEC-0272)

> **Prompt 17 (2026-11-18):** superseded where it differs by `MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md`, `MIA_OS_FINAL_MVP_AND_RELEASE_DEFINITION.md` and `MIA_OS_FINAL_MIGRATION_AND_DATA_CONTINUITY_PLAN.md`. Corrections: proof of concept 2's headless boot, update and rollback **passed** on 2026-11-16 (GitHub run 43872077107), so "boot to do" is wrong; the login manager is Plasma Login Manager, not SDDM; DEC-0269, 0270 and 0272 are approved (`docs/DECISIONS.md`).

*Claude (Opus), 2026-11-18. Planning only.*

**His board has one M.2 slot** (Prompt 06), so the original dual-boot plan (DEC-0157) becomes: MIA OS on the new 4 TB
drive; the current 1 TB Windows drive kept **intact** as the fallback, in a USB enclosure (Q-102) or put back in the
slot if MIA OS has to wait.

| Step | What | Undo |
|---|---|---|
| 1 | On Windows: a fresh MIA backup (encrypted), the recovery key at hand, the phone synced | — |
| 2 | Swap the drives: the 4 TB in the slot, the 1 TB into the enclosure, untouched | put the 1 TB back |
| 3 | Install MIA OS from the USB stick (the image's ISO) | — |
| 4 | Sign in; restore the backup; enter the recovery key (sealed stores open on Linux, DEC-0169) | restore again |
| 5 | Pair the phone; sync; the glasses through the phone | — |
| 6 | Check: every store's counts match Windows' (a migration report in code) | — |
| 7 | A week as his main system; Windows reachable by booting from the enclosure | boot the enclosure |
| 8 | After a month and his yes, the 1 TB can be reused | — |

**What moves:** his data folder and settings (the backup), his models (re-downloaded or copied), his files (copied from
the 1 TB through the enclosure). **What doesn't:** Windows programs (their Linux or Flatpak equivalents listed by
a migration check).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-IMP-002 | A migration report shall compare every store's record counts on Windows and on MIA OS, and the move shall not count as done until they match. | Must | MVP | PC | Partial (FW-07a: `core/migration.py` counts and hashes every store, `compare` names a mismatch; the report on MIA OS is FW-07b) | T | DEC-0272, REQ-CMP-002 → 16 |
