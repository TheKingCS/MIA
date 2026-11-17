# MIA OS: backups and data protection (Prompt 13 §24)

*Claude (Opus), 2026-11-18. Planning only. Recovery itself: Prompt 14.*

| Protection | How | State |
|---|---|---|
| Nightly backup | `core/auto_backup.py`, encrypted with his passphrase | built |
| Sealed files stay sealed in a backup | yes (they're copied sealed) | built |
| A second copy off the PC | the phone's synced copy; an external drive he chooses | partial |
| Restore tested | a restore drill into a scratch folder, monthly, checked by code | to add |
| Undo | recent changes, from the undo log | built |
| Btrfs snapshots (MIA OS) | before every update | planned |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-037 | Backups shall be encrypted, kept in at least two places, and restored in a monthly drill checked by code. | Should | R1 | All | Partial | T | DEC-0252 → 13, 14 |
