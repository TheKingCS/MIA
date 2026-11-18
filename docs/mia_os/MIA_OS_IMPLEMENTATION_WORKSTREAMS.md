# MIA OS: workstreams (Prompt 16; DEC-0273)

> **Prompt 17 (2026-11-18):** superseded where it differs by `MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md`, `MIA_OS_FINAL_MVP_AND_RELEASE_DEFINITION.md` and `MIA_OS_FINAL_MIGRATION_AND_DATA_CONTINUITY_PLAN.md`. Corrections: proof of concept 2's headless boot, update and rollback **passed** on 2026-11-16 (GitHub run 43872077107), so "boot to do" is wrong; the login manager is Plasma Login Manager, not SDDM; DEC-0269, 0270 and 0272 are approved (`docs/DECISIONS.md`).

*Claude (Opus), 2026-11-18.*

| Workstream | Covers | Owner | Prompt |
|---|---|---|---|
| W-OS | the image, sessions, the helper, updates, Secure Boot, the disk | Claude | 05, 14, 15 |
| W-SHELL | MIA's session, window strip, modes, safe mode | Claude (function), Muse (look) | 10, 11 |
| W-SEC | approval binding, injection set, household key, hash-chained log, lockdown, sealing every store | Claude | 13 |
| W-REL | readiness, restart limits, snapshots, the off-PC backup, the restore drill | Claude | 14 |
| W-DEV | the Linux suite job, hash locks, signed releases, SBOMs, pinned actions | Claude | 15 |
| W-SELF | the capability truth registry, orb states, the protected list growth | Claude | 09, 11 |
| W-LOOK | Light theme, interface sounds, the Theme Studio from a picture | Claude, Muse | 11 |
| W-DEV-ICES | device records, scoped keys, lost-phone erase, the household display, the laptop | Claude | 12 |
| W-MIG | the migration report, the move itself | Claude, Zac | 16 |
| W-SPEC | specialists, Forge, Night School | Claude, MIA | 25, 26 |
| W-HOME | the greenhouse link, actions to the node | Claude | 12, homestead |

Each runs on the task board (`work/tasks`, `tools.work`).
