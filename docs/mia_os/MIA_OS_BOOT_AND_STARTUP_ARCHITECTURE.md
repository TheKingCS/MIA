# MIA OS: boot, updates, recovery and reliability (Prompt 14)

*Claude (Opus), 2026-11-18, on Zac's go ("Lets build prompt 14"). Planning only: nothing was installed, updated or
reconfigured. The prompt is `prompts/14_*.md`. Twenty-five documents sit beside this one (section 9). The
requirements Prompt 04 left to this prompt (REQ-REL-004, 006 to 009, 013) are answered here; new ones start at
REQ-REL-015.*

## 1. The headline

1. **The machine never waits for MIA.** Firmware → the boot loader → the kernel → the encrypted disk unlocked by the
   TPM → systemd → the login screen; the conventional desktop is usable within 10 seconds of choosing it whether MIA
   started or not (REQ-PER-002). MIA's runtime starts as his user service, her shell when the runtime says it's ready
   (DEC-0255).
2. **Readiness has levels, and she says which:** core ready (records, actions, screens), voice ready, models warm,
   all ready. A screen opens on "core ready"; her orb says when answers in words aren't ready yet (DEC-0255).
3. **systemd keeps each part alive and apart**: the runtime, the shell, Ollama, the helper and the node link are
   separate units with restart limits and watchdogs; one failing never takes the others (DEC-0256, REQ-REL-003, 004).
4. **Updates are whole and reversible**: the OS image with MIA's code in it is staged, applied at a restart he
   allows, and if the new one fails to boot healthy, the machine boots the previous one by itself (bootc and
   greenboot; DEC-0257, REQ-REL-009).
5. **His data survives anything short of losing every copy**: atomic writes (built), the previous copy on a big
   shrink (built), Btrfs snapshots before every update and hourly, the append-only history, nightly encrypted backups
   (built) kept in two places, and a monthly restore drill checked by code (DEC-0258, DEC-0259).
6. **When MIA misbehaves, he still has a computer**: Plasma at login, MIA's safe mode (no jobs, no models, the
   default theme), and the previous deployment in the boot menu (DEC-0260).
7. **Objectives he can hold her to** (DEC-0261): his records never lost to a crash; at most a day lost if the PC
   is destroyed, none if the phone holds a fresh sync; a replacement PC running his MIA in about two hours.

## 2. The audit (2026-11-18)

| Part | Built | Where |
|---|---|---|
| Startup order (Windows) | splash → core services → modules → profile → main window | `core/application.py` |
| Headless runtime | the whole MIA with no window; instance lock | `core/runtime.py`, `core/instance_lock.py` |
| Refusing unreadable sealed data | a runtime won't start on data it can't open | `core/at_rest.start_problem` |
| systemd units | the runtime and the kiosk as user services | `deploy/mia-runtime.service`, `deploy/mia.service`, `deploy/install_runtime.sh` |
| Atomic writes and the previous copy | write, replace; keep `.prev` on a big shrink | `core/atomic_write.py` |
| Corrupt store recovery | starts empty, keeps the bad file, tells him | `core/data_recovery.py` |
| Backups | nightly, encrypted, restore checked before it's applied | `core/auto_backup.py`, `core/backup_manager.py` |
| Undo | recent changes | `core/undo_log.py` |
| Self-repair, job backoff, homeostasis | restart Ollama, back off failing jobs, ease off when busy | `core/self_repair.py`, `core/scheduler.py`, `core/homeostasis.py` |
| Her own code | merge, suite, automatic revert | `core/dev_lab.py` |
| Setup check | what works on this device and what to fix | `core/system_check.py` |
| OS updates, rollback, snapshots, safe mode | — | planned (Prompt 05: DEC-0157, 0189, 0193) |

## 3. Decisions (records in `MIA_OS_RELIABILITY_TECHNOLOGY_EVALUATION.md` §2)

| DEC | Decision | Status |
|---|---|---|
| DEC-0255 | The OS boots without MIA; MIA starts as his user service with readiness levels | PROPOSED |
| DEC-0256 | Each part its own systemd unit with restart limits and a watchdog | PROPOSED |
| DEC-0257 | Whole-image updates, applied at a restart he allows, rolled back by themselves on a failed boot | PROPOSED |
| DEC-0258 | Data reliability in layers: atomic writes, snapshots, the append-only history, integrity checks | PROPOSED |
| DEC-0259 | Backups in two places, encrypted, restored monthly by a drill | PROPOSED |
| DEC-0260 | Plasma, safe mode and the previous deployment as the fallbacks | PROPOSED |
| DEC-0261 | Reliability objectives | PROPOSED |

## 4. Questions for Zac

`MIA_OS_RELIABILITY_OPEN_QUESTIONS.md`: Q-95 (when updates install), Q-96 (where the second backup lives), Q-97 (a
UPS), Q-98 (a monthly restore drill on its own).

## 5. Boundaries

Prompt 15 builds and signs the images; Prompt 16 the order of building; Prompt 17 the review.

## 6. Sources

The repository, read 2026-11-18; Prompts 04, 05, 06, 13; DEC-0155, 0157, 0189 to 0195, 0222, 0252. bootc and
greenboot (Fedora), systemd (`Restart=`, `StartLimitBurst=`, `WatchdogSec=`, `Type=notify`), snapper on Btrfs.

## 7. What it means for him

He turns the PC on and has a computer in seconds, MIA a little after. An update that goes wrong undoes itself at
the next start. His things are never lost to a crash, and a broken PC is a two-hour job, not a lost life.

## 8. Requirements

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-015 | MIA shall report readiness in levels (core, voice, models, all), and her screens shall open at core readiness, saying what isn't ready yet. | Should | R1 | All | Partial | T | DEC-0255 → 14 |

## 9. The documents

`MIA_OS_MIA_FIRST_STARTUP_EXPERIENCE.md`, `MIA_OS_SERVICE_STARTUP_AND_DEPENDENCY_MODEL.md`,
`MIA_OS_HEALTH_CHECK_AND_READINESS_ARCHITECTURE.md`, `MIA_OS_FAILURE_ISOLATION_AND_FAULT_CONTAINMENT.md`,
`MIA_OS_CRASH_RECOVERY_AND_SESSION_RESTORATION.md`, `MIA_OS_SAFE_MODE_AND_DESKTOP_FALLBACK.md`,
`MIA_OS_SYSTEM_UPDATE_ARCHITECTURE.md`, `MIA_OS_ATOMIC_UPDATES_AND_ROLLBACK.md`,
`MIA_OS_APPLICATION_AND_COMPONENT_UPDATES.md`, `MIA_OS_CONFIGURATION_MANAGEMENT_AND_RECOVERY.md`,
`MIA_OS_DATABASE_AND_MEMORY_RELIABILITY.md`, `MIA_OS_BACKUP_ARCHITECTURE.md`, `MIA_OS_RESTORE_AND_DISASTER_RECOVERY.md`,
`MIA_OS_STORAGE_AND_FILESYSTEM_RELIABILITY.md`, `MIA_OS_AI_SERVICE_RELIABILITY.md`,
`MIA_OS_DISTRIBUTED_DEVICE_RELIABILITY.md`, `MIA_OS_BOOT_INTEGRITY_AND_RECOVERY_SECURITY.md`,
`MIA_OS_RELIABILITY_OBJECTIVES.md`, `MIA_OS_DIAGNOSTICS_AND_USER_COMMUNICATION.md`,
`MIA_OS_RELIABILITY_TESTING_AND_FAILURE_SIMULATION.md`, `MIA_OS_RELIABILITY_ARCHITECTURE_DIAGRAMS.md`,
`MIA_OS_RELIABILITY_SCENARIO_ANALYSIS.md`, `MIA_OS_RELIABILITY_TECHNOLOGY_EVALUATION.md`,
`MIA_OS_RELIABILITY_ACCEPTANCE_CRITERIA.md`, `MIA_OS_RELIABILITY_OPEN_QUESTIONS.md`.

## Engineering (Prompt 15, 2026-11-18)

Images are booted in a VM before they're published (`MIA_OS_LINUX_IMAGE_BUILD_INFRASTRUCTURE.md`).

## Implementation (Prompt 16, 2026-11-18)

Booting the image in a VM is milestone M2, the first on the critical path after the GPU proof (`MIA_OS_IMPLEMENTATION_CRITICAL_PATH.md`).
