# MIA OS: his data through every stage (Prompt 16)

*Claude (Opus), 2026-11-18.*

| Stage | His data lives | Protected by |
|---|---|---|
| 0 | Windows (the PC), the phone | atomic writes, sealed stores, nightly backups, sync |
| 1 to 2 | unchanged (the proofs and the VM use none of it) | — |
| 3, the move | copied: Windows → backup → MIA OS; the phone as a second copy | the migration report; Windows intact |
| 3, the week | MIA OS; the phone syncing; Windows frozen as it was | backups; snapshots |
| After | MIA OS, the phone, the off-PC backup | DEC-0258, 0259 |

**Never during the move:** deleting anything on Windows; a sync from a device that hasn't seen the moved data (the
phone re-pairs after the move and syncs against MIA OS, its base reset, so it can't push old copies back).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-IMP-005 | After the move, the phone shall re-pair with MIA OS and reset its sync base, so no stale copy overwrites moved data. | Must | MVP | Phone | New | T | DEC-0272, DEC-0243 → 16 |
