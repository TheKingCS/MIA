# MIA OS: reliability technology evaluation and decision records (Prompt 14)

*Claude (Opus), 2026-11-18. Planning only. DEC-0255 to 0261 are PROPOSED.*

## 1. Technologies

| Need | Options | Recommendation | Why |
|---|---|---|---|
| Atomic OS updates | bootc / rpm-ostree (Fedora Atomic), A/B partitions (RAUC), snapshots alone (snapper + a mutable OS) | **bootc** | approved base (DEC-0189); images from the repository; rollback built in |
| Boot health and rollback | greenboot, a custom check | **greenboot** | Fedora's, works with ostree |
| Service supervision | systemd (`Restart=`, `StartLimitBurst=`, `WatchdogSec=`, `Type=notify`, slices) | **systemd** | already the plan (DEC-0195) |
| Data snapshots | snapper on Btrfs, Timeshift | **snapper** | Fedora's tool for Btrfs |
| Backups | MIA's own (exists), restic, Borg | **MIA's own for his data**; restic optional for the off-PC copy | his encrypted format is built and restore-checked |
| Memory pressure | systemd-oomd | **systemd-oomd** | Fedora's default |
| Disk health | smartmontools | **smartd** | |
| Boot splash | Plymouth | **Plymouth with MIA's theme** | |

## 2. Decision records

### DEC-0255: the OS boots without MIA; readiness in levels
Requirements: REQ-REL-015, 016, 017, 032. MIA's units start after login as his user services, Wanting optional
services; the shell shows what isn't ready.

### DEC-0256: each part its own unit, restart limits, a watchdog, its own slice
Requirements: REQ-REL-018, 019, 033, REQ-REL-004.

### DEC-0257: whole-image updates at a restart he allows, rolled back by themselves
Requirements: REQ-REL-023, 024, 025, 034, REQ-REL-009.

### DEC-0258: data reliability in layers
Requirements: REQ-REL-026, 027, 031. Atomic writes, `.prev`, Btrfs snapshots, the append-only history, start-time
integrity checks.

### DEC-0259: backups in two places, restored monthly by a drill
Requirements: REQ-REL-028, 029, REQ-REL-007.

### DEC-0260: Plasma, safe mode and the previous deployment as the fallbacks
Requirements: REQ-REL-022, REQ-REL-008.

### DEC-0261: reliability objectives
Requirements: REQ-REL-030, 035, 036. No records lost to a crash; at most a day if the PC is destroyed; a new PC in
about two hours; every recovery told.
