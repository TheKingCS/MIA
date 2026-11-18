# MIA OS: the final migration and data continuity plan (Prompt 17)

*Claude (Opus), 2026-11-18. Version 1.0. Governs over `MIA_OS_EXISTING_SYSTEM_MIGRATION_STRATEGY.md` and
`MIA_OS_USER_DATA_AND_MIGRATION_CONTINUITY.md` where they differ. Base: DEC-0272 (approved): one M.2 slot, MIA OS on
the new 4 TB drive, the 1 TB Windows drive kept untouched. Strengthened after Codex's F-05.*

## 1. What moves, how it's checked

| What | How it moves | How it's verified |
|---|---|---|
| His MIA data (every personal and household store, the history, links, vaults) | the encrypted backup, restored on MIA OS | each store's record count **and content hash** match (REQ-IMP-009), sealed stores opened and re-sealed under the Linux key |
| Settings | in the backup (`config/config.json` and per-person settings) | the runtime reports the same model, voice and theme |
| His files outside MIA | copied from the Windows drive through the enclosure | a hash sample across his folders |
| Models | re-downloaded by Ollama tag (or copied from the Windows drive's model folder) | the bench's figures |
| The phone | re-paired; its sync base reset so it can't push an old copy back (REQ-IMP-005) | a test edit round-trips |
| Windows programs | not moved; each one he uses gets its Linux answer before the move (REQ-CMP-003) | the list reviewed with him |

## 2. The procedure (MV-01), each step a gate

| # | Step | Gate to continue |
|---|---|---|
| 0 | Rehearsed in the VM on a synthetic profile (FW-07) | the rehearsal report all green |
| 1 | HW-01 passed (the GPU under Fedora) | the bar met |
| 2 | HW-02: Windows tried from the enclosure | known: it boots, or the fallback is the drive back in the slot |
| 3 | On Windows: a fresh backup, the manifest written, the phone synced, MIA's recovery key at hand (never pasted into chat) | the backup verifies by a restore into a scratch folder |
| 4 | The drives swapped | the 1 TB in its enclosure, never mounted for writing |
| 5 | MIA OS installed from the USB stick, with encryption (FW-05); the LUKS recovery key printed | boots, unlocks with TPM and PIN |
| 6 | Restore; MIA's recovery key entered | the verification report all green; **any mismatch stops the move** |
| 7 | Files copied; the phone re-paired | the hash sample matches; a test edit round-trips |
| 8 | A week of use (MV-02) | Zac passes the MVP gate |
| 9 | After a month and his yes, the 1 TB may be reused | Alpha's exit condition |

**Undo at any step:** put the 1 TB back in the slot (or boot it from the enclosure if HW-02 said it can) and Windows is
exactly as it was. Nothing in this procedure writes to it.

## 3. Continuity through the stages

| Stage | Where his data lives | Protection |
|---|---|---|
| Now to Foundation | Windows and the phone | atomic writes, sealed stores, nightly backups, sync; the VM never touches his data |
| The move | copied: Windows → backup → MIA OS; the phone a second copy | the manifest; Windows untouched |
| The week and after | MIA OS, the phone, the off-PC backup (DEC-0259) | snapshots before updates, nightly backups, the monthly restore drill |

## 4. Migrating MIA's own subsystems (Prompt 17's scenario M)

The supplemental directive asks that nothing working be rewritten without cause. No MIA subsystem is replaced for
MIA OS. What changes is where each runs and what it calls: the runtime from a desktop app to a user service (built on
Windows already, DEC-0155); the sealing key from Windows DPAPI to the system credential (built, DEC-0169); the shell
from the Qt window to a session (FW-03). Each keeps its tests, runs on both systems while Windows is in use, and is cut
over at MV-01 with the Windows drive as the rollback.
