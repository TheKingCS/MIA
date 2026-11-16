# MIA OS: reliability and degradation requirements (Prompt 04, deliverable 9, with §17)

*Claude (Opus), 2026-11-15. Planning only. Row format: [SYSTEM_REQUIREMENTS](MIA_OS_SYSTEM_REQUIREMENTS.md) §1. Boot,
update and recovery mechanics are Prompt 14's.*

## 1. What keeps working when something fails (§17)

| Failure | Keeps working | Stops, and says so | Recovers by |
|---|---|---|---|
| No internet | every local record, app, model, search, voice, home control on the LAN, the glasses through the phone | online lookups, feeds, World Intelligence, sync away from home, cloud models | retrying when back (homeostasis defers online jobs) |
| A cloud model down | everything (the MVP uses none) | that model's tasks fall back to local | REQ-AI-013 |
| The local model fails or the GPU driver breaks | screens, actions, search, lookups answered by code; the conventional desktop | conversation beyond lookups ("the model is unavailable") | restart the runner; the CPU fallback for the 3B model |
| MIA's runtime crashes | the conventional desktop, the OS, conventional apps | MIA's screens show the recovery page | systemd restarts the service; three failures in a row stop restarting and say so |
| An app fails | every other app; MIA herself | that app (its status: failing, with why) | the Fix-It Log; the lab |
| A shared platform service fails (the scheduler, the gate) | screens and actions | that service's work (jobs wait; messages wait) | per-service isolation; restart |
| A device disconnects | everything else | that device's capabilities (unreachable, last heard) | reconnects; sync catches up |
| Storage full | reading | writes refused with a plain message; heavy jobs deferred | homeostasis's disk check; cleanup offered |
| A store's file unreadable | every other store | that store starts empty, the file copied aside, the person told | backups; the copy aside |
| A peripheral stops responding | everything else | that capability | the OS's own recovery |
| An update fails | the previous deployment | — | boot the previous deployment |
| A session interrupted (power, crash) | — | — | atomic writes mean no half-written records; waiting runs resume |

**Functions that must never depend on MIA's reasoning:** booting, logging in, disk unlock, the conventional desktop,
recovery, backups and restore, alarms, crisis numbers (`core/safety_floor.py`), the action contract's checks, the
grant check, the communication gate's rules, device safety interlocks.

## 2. Requirements

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-001 | Every function in the MVP except conversation beyond lookups shall work with no model available. | Must | MVP | All | Exists today | T: the suite runs without a model; S-14 | E3, E5 → 07, 14 |
| REQ-REL-002 | Every function in the MVP shall work with no internet connection, except the ones whose purpose is online (lookups, feeds, sync away from home). | Must | MVP | All | Exists today | M: S-12 with the network unplugged | E3 → 14 |
| REQ-REL-003 | A failing job, app or store shall not stop any other; each failure is isolated and recorded. | Must | MVP | All | Exists (scheduler isolation, per-store recovery, app statuses) | T: `tests/test_scheduler.py`, `tests/test_living_system.py` | P13 → 05 |
| REQ-REL-004 | The runtime shall be restarted automatically after a crash, at most three times in a row before it stops and says so. | Must | MVP | PC, Pi | Partial (the systemd unit restarts; the limit New) | T | P13 → 14 |
| REQ-REL-005 | Every store write shall be atomic (write, then replace), so an interruption never leaves a half-written record. | Must | MVP | All | Exists (`core/atomic_write.py`) | T | P13 → 05 |
| REQ-REL-006 | An unreadable store shall start empty with the bad file kept aside and the person told; it never stops MIA. | Must | MVP | All | Exists (`core/data_recovery.py`) | T | P13 → 14 |
| REQ-REL-007 | A full backup shall run nightly and a restore shall bring back every store to the backup's moment, rehearsed at least once a release. | Must | MVP | PC | Exists (`core/auto_backup.py`; restore tested) | T, D | P13 → 14 |
| REQ-REL-008 | A safe mode shall start MIA with no jobs, no extensions and no model, for diagnosis. | Should | R1 | PC | New | D | §17 → 14 |
| REQ-REL-009 | A failed update shall leave the machine booting the previous deployment with nothing lost. | Must | MVP | PC | Planned (bootc) | D | DEC-0157 → 14 |
| REQ-REL-010 | Only one MIA shall run per data folder; a second start is refused, not allowed to overwrite. | Must | MVP | All | Exists (`core/instance_lock.py`) | T | P13 → 05 |
| REQ-REL-011 | Deferrable work shall wait while the machine is busy, on low battery, offline or nearly out of disk, and say so once. | Must | MVP | All | Exists (`core/homeostasis.py`) | T | DEC-0173 → 05 |
| REQ-REL-012 | A job failing three times in a row shall back off (longer intervals, at most six hours) and say so once, returning to normal when it works. | Must | MVP | All | Exists | T: `tests/test_homeostasis.py` | DEC-0173 → 05 |
| REQ-REL-013 | After an interruption, waiting skill runs, pending proposals within their day and drafts shall be where they were. | Should | R1 | All | Partial (skill runs and drafts persist; proposals are in memory) | T | P4 → 14 |
| REQ-REL-014 | Every failure the person can see shall be in the Fix-It Log with what happened, and repeated failures grouped as one issue. | Must | MVP | All | Exists (`core/failure_log.py`) | T | DEC-0049 → 14 |
