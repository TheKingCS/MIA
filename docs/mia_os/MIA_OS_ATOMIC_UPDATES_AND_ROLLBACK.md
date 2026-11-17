# MIA OS: atomic updates and rollback (Prompt 14)

*Claude (Opus), 2026-11-18. Planning only.*

| Guarantee | Mechanism |
|---|---|
| An update is all or nothing | bootc/ostree deployments: the new one is complete before it's chosen |
| The old one stays | the previous deployment kept until the next update succeeds |
| A failed boot undoes itself | greenboot: health checks fail → the boot counter → the previous deployment |
| His data is safe across it | a Btrfs snapshot of `/home` and `/var` before applying (snapper) |
| Data written by a newer MIA reads in an older one | store changes are additive (new fields default); a migration that isn't is versioned and reversible |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-024 | Before an update is applied, his data shall be snapshotted, and after a rollback the older MIA shall still read it. | Must | MVP | PC | Planned | D: PoC 2 | DEC-0257, REQ-REL-009 → 14 |
