# MIA OS: adopting it in stages (Prompt 16)

> **Prompt 17 (2026-11-18):** superseded where it differs by `MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md`, `MIA_OS_FINAL_MVP_AND_RELEASE_DEFINITION.md` and `MIA_OS_FINAL_MIGRATION_AND_DATA_CONTINUITY_PLAN.md`. Corrections: proof of concept 2's headless boot, update and rollback **passed** on 2026-11-16 (GitHub run 43872077107), so "boot to do" is wrong; the login manager is Plasma Login Manager, not SDDM; DEC-0269, 0270 and 0272 are approved (`docs/DECISIONS.md`).

*Claude (Opus), 2026-11-18.*

| Stage | His everyday computer | MIA | Fallback |
|---|---|---|---|
| Now | Windows | the desktop app | — |
| Trying (stage 1) | Windows | — | — (a USB stick, nothing installed) |
| The VM (stage 2) | Windows | — | — |
| The week (stage 3) | MIA OS | MIA OS | the Windows drive in its enclosure |
| After a month | MIA OS | MIA OS | the previous image; backups |
| R1 | MIA OS, the laptop, the TV display | everywhere | — |

**He decides each step**: no stage starts without his go, and he can stop at any.
