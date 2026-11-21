# MIA OS: work packages (Prompt 16)

> **Prompt 17 (2026-11-18):** superseded where it differs by `MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md`, `MIA_OS_FINAL_MVP_AND_RELEASE_DEFINITION.md` and `MIA_OS_FINAL_MIGRATION_AND_DATA_CONTINUITY_PLAN.md`. Corrections: proof of concept 2's headless boot, update and rollback **passed** on 2026-11-16 (GitHub run 43872077107), so "boot to do" is wrong; the login manager is Plasma Login Manager, not SDDM; DEC-0269, 0270 and 0272 are approved (`docs/DECISIONS.md`).

*Claude (Opus), 2026-11-18. Each package ends with its tests, documentation and gate (DEC-0273). Stage 0 packages
build on Windows now and carry over.*

| ID | Package | Stream | Stage | Milestone | Size |
|---|---|---|---|---|---|
| WP-01 | The lockdown phrase (Q-93). **Built 2026-11-20** (`core/lockdown.py`) | W-SEC | 0 | M0 | S |
| WP-02 | Approvals bound to their parameters (REQ-SEC-016) | W-SEC | 0 | M0 | S |
| WP-03 | Outside content marked at every entry; the injection test set | W-SEC | 0 | M0 | M |
| WP-04 | Every personal store sealed; a test over the classes | W-SEC | 0 | M0 | M |
| WP-05 | Hash-chained security log | W-SEC | 0 | M0 | S |
| WP-06 | Light theme; interface sounds; the Theme Studio from a picture | W-LOOK | 0 | M0 | M |
| WP-07 | The orb's states driven by events | W-SELF | 0 | M0 | S |
| WP-08 | The capability truth registry with states and evidence | W-SELF | 0 | M0 | M |
| WP-09 | The restore drill; the off-PC backup copy | W-REL | 0 | M0 | S |
| WP-10 | Device records, scoped keys, the lost-phone erase, conflict notes | W-DEVICES | 0 | M0 | M |
| WP-11 | The Linux suite job; uv lock with hashes; pinned actions | W-DEV | 0 | M0 | S |
| WP-12 | Her merged changes pushed with the daily summary (Q-100) | W-DEV | 0 | M0 | S |
| WP-13 | PoC 1 on his GPU | W-OS | 1 | M1 | S (his hour) |
| WP-14 | The image boots in a VM; the runtime at core ready; `sd_notify` and watchdog | W-OS, W-REL | 2 | M2 | M |
| WP-15 | SDDM sessions; MIA's session under KWin; safe mode | W-SHELL | 2 | M3 | M |
| WP-16 | bootc updates, greenboot, snapshots; the helper's first operations | W-OS | 2 | M4 | L |
| WP-17 | Secure Boot and the TPM-unlocked disk | W-OS | 2 | M4 | M |
| WP-18 | Signed images, SBOMs, releases; the phone app from secrets | W-DEV | 2 | M5 | M |
| WP-19 | The migration report and the move | W-MIG | 3 | M6 | M |
| WP-22a | *Order (Zac, Q-104): WP-22 first, then WP-20, then WP-21* | — | 4 | M8 | — |
| WP-20 | The household display on the TV (the Pi, cage, the household key) | W-DEVICES | 4 | M8 | M |
| WP-21 | The laptop as a full engine | W-DEVICES | 4 | M8 | M |
| WP-22 | Recall over conversations; workspaces; the UAL on any selection; cross-app plans | W-SELF, W-SHELL | 4 | M8 | L |
