# MIA OS: storage reliability (Prompt 14)

*Claude (Opus), 2026-11-18. Planning only. Layout: Prompt 05 (DEC-0193).*

| Concern | How |
|---|---|
| Filesystem | Btrfs on LUKS2: checksums catch silent corruption; snapshots |
| Disk health | SMART read daily (Prompt 09); a warning when it degrades |
| Disk filling | homeostasis eases off near full; old snapshots and caches pruned first, never his data |
| Power loss | atomic writes; Btrfs's copy-on-write; a UPS (Q-97) for long runs |
| The 1 TB drive | replaced by a 4 TB one (Q-65): restore from backup onto it |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-031 | When the disk nears full, snapshots and caches shall be pruned before anything else, and his data never. | Must | R1 | PC | Partial (homeostasis) | T | DEC-0258 → 14 |
