# MIA OS: store and memory reliability (Prompt 14; DEC-0258)

*Claude (Opus), 2026-11-18. Planning only. MIA's stores are JSON files, sealed where listed; there's no database
server to fail.*

| Protection | How | Exists |
|---|---|---|
| No half-written file | write to a temp file, fsync, replace (`atomic_write_text`) | yes |
| A big shrink kept | `.prev` beside the file | yes |
| A damaged file | that store starts empty, the file aside, he's told | yes |
| The history | append-only, never rewritten; merged by event id | yes |
| Undo | recent changes restorable | yes |
| Integrity check | on start, each store parses; a sealed one opens | partial |
| Snapshots | Btrfs, hourly and before updates | planned |
| The recall index | derived, rebuilt from the stores | yes |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-027 | His data folder shall be snapshotted hourly (kept 48 hours) and daily (kept 30 days) on MIA OS. | Should | R1 | PC | Planned | D | DEC-0258, DEC-0193 → 14 |
