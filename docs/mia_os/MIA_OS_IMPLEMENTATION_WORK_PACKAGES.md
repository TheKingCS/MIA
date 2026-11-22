# MIA OS: work packages (Prompt 16)

> **Prompt 17 (2026-11-18):** superseded where it differs by `MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md`, `MIA_OS_FINAL_MVP_AND_RELEASE_DEFINITION.md` and `MIA_OS_FINAL_MIGRATION_AND_DATA_CONTINUITY_PLAN.md`. Corrections: proof of concept 2's headless boot, update and rollback **passed** on 2026-11-16 (GitHub run 43872077107), so "boot to do" is wrong; the login manager is Plasma Login Manager, not SDDM; DEC-0269, 0270 and 0272 are approved (`docs/DECISIONS.md`).

*Claude (Opus), 2026-11-18. Each package ends with its tests, documentation and gate (DEC-0273). Stage 0 packages
build on Windows now and carry over.*

| ID | Package | Stream | Stage | Milestone | Size |
|---|---|---|---|---|---|
| WP-01 | The lockdown phrase (Q-93). **Built 2026-11-20** (`core/lockdown.py`) | W-SEC | 0 | M0 | S |
| WP-02 | Approvals bound to their parameters (REQ-SEC-016). **Built 2026-11-20** (`binding_of`, core/actions.py) | W-SEC | 0 | M0 | S |
| WP-03 | Outside content marked at every entry; the injection test set. **Built 2026-11-20** (`browser_safety.outside`, `tool_loop.OUTSIDE_WHAT`, `tests/test_injection.py`) | W-SEC | 0 | M0 | M |
| WP-04 | Every personal store sealed; a test over the classes. **Begun 2026-11-20, all but the budget 2026-11-21**: every personal file is sealed (123 whole, 9 a line at a time), public (5), named but never kept as a file (`NO_FILE`, 4) or on `at_rest.NOT_SEALED_YET` with why (`tests/test_sealed_stores.py`, a list that only shrinks: 7 left, the budget's, waiting on the Plaid work); sync's last-synced copies are sealed with their files | W-SEC | 0 | M0 | M |
| WP-05 | Hash-chained security log. **Built 2026-11-22** (`security_log.link`/`check_chain`/`holds`; the Sign-ins page keeps the head on the viewing device and asks next time; REQ-SEC-034) | W-SEC | 0 | M0 | S |
| WP-06 | Light theme; interface sounds; the Theme Studio from a picture. **Mostly built 2026-11-22**: interface sounds from the orb's real changes (REQ-VIS-023), auto glass light while a model generates (REQ-VIS-026, 012); the Studio from a picture was A7 (REQ-VIS-016). **The Light theme waits on Q-115** (a light theme needs darker shades of the meaning colours, which DEC-0136 forbids a theme to change) | W-LOOK | 0 | M0 | M |
| WP-07 | The orb's states driven by events. **Built 2026-11-22** (`orb_state.LOOK`: words and a still glyph per state, shown under reduced motion; `needs-you` from waiting cards, `offline` from the model not answering, speaking while her reply plays; REQ-VIS-010, most of 009) | W-SELF | 0 | M0 | S |
| WP-08 | The capability truth registry with states and evidence. **Built 2026-11-22** (`core/capability_registry.py`: a record per app, eight states incl. degraded and unverified, each change kept with its evidence, no write path but the rebuild; Diagnostics' "What I Can Do"; REQ-SLF-003/004/005) | W-SELF | 0 | M0 | M |
| WP-09 | The restore drill; the off-PC backup copy. **Built 2026-11-22** (`core/restore_drill.py`, monthly, every store opened in a scratch folder; `auto_backup.copy_offsite` to `backup.offsite_folder`, kept 7 nightly, 4 weekly, 6 monthly; REQ-SEC-037). Waits on Zac: the drive to choose | W-REL | 0 | M0 | S |
| WP-10 | Device records, scoped keys, the lost-phone erase, conflict notes. **Built 2026-11-22** (`linked_devices.record`/`allows`/`mark_lost`, 410 with X-MIA-Erase, `home_link.erase_here`; Sign-ins' Linked Devices with Lost; conflict notes were built with sync, LS-05; REQ-DST-005/029/030, REQ-DEV-002) | W-DEVICES | 0 | M0 | M |
| WP-11 | The Linux suite job; uv lock with hashes; pinned actions. **Done with FW-01/FW-02** (checked 2026-11-22: `suite-linux` in mia-os-poc.yml on every push, `os/requirements.lock` from `uv pip compile --generate-hashes`, every action pinned to a full commit and every workflow's `permissions:` set, each held by `tests/test_ci_workflows.py`) | W-DEV | 0 | M0 | S |
| WP-12 | Her merged changes pushed with the daily summary (Q-100). **Built 2026-11-22** (`core/lab_push.py`: only her own commits, never forced or rebased, held when GitHub has newer; after the daily summary; on the lab's protected list) | W-DEV | 0 | M0 | S |
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
