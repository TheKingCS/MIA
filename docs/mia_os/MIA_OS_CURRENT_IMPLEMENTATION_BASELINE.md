# MIA OS: where things stand (Prompt 16)

> **Prompt 17 (2026-11-18):** superseded where it differs by `MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md`, `MIA_OS_FINAL_MVP_AND_RELEASE_DEFINITION.md` and `MIA_OS_FINAL_MIGRATION_AND_DATA_CONTINUITY_PLAN.md`. Corrections: proof of concept 2's headless boot, update and rollback **passed** on 2026-11-16 (GitHub run 43872077107), so "boot to do" is wrong; the login manager is Plasma Login Manager, not SDDM; DEC-0269, 0270 and 0272 are approved (`docs/DECISIONS.md`).

*Claude (Opus), 2026-11-18. From the requirements matrix and the audits of Prompts 01 to 15.*

## 1. The requirements

478 requirements: 175 exist, 165 partial, 38 planned, 100 new (the matrix, `MIA_OS_REQUIREMENTS_TRACEABILITY_MATRIX.md`).

## 2. Built and working (Windows; most also tested on Linux)

The engine (~6,800 tests), 57 apps, 482 action kinds with tiers and grants, Approve From Now On by screen and voice,
the web front end (109 screens) with area dashboards, Talk, search, the Theme Studio, the ambient second monitor,
the phone's full engine with sync, the glasses, specialists on local models (15 passing their bench), Night School
and the lab with Claude's pass and a daily summary, self-repair, the protected list, recall by meaning (first slice),
noting what he's working on, the communication gate with focus, encrypted vaults and 56 sealed stores, the security
log, two-step, nightly encrypted backups, the headless runtime with systemd units, the image's Containerfile.

## 3. Designed, not built (the bigger pieces)

| Piece | Prompt |
|---|---|
| The image booting with SDDM sessions, MIA's session under KWin, the helper, bootc updates and rollback | 05, 10, 14 |
| Disk encryption with the TPM, safe mode | 13, 14 |
| Approval binding, injection test set, household key, hash-chained log, lockdown | 13 |
| The capability truth registry, orb states driven by events, Light theme, interface sounds | 09, 11 |
| Device records and scoped keys, lost-phone erase, conflict notes | 12 |
| Restore drill, off-PC backup copy | 14 |
| Hash-locked dependencies, a Linux suite job, signed releases, SBOMs | 15 |

## 4. Waiting on Zac

A USB stick (PoC 1); the 4 TB drive; the phone's signing key (DEC-0160); an external drive and a UPS; the laptop's
model; trying the second monitor.
