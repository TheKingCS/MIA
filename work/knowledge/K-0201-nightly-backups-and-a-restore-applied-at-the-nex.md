---
id: K-0201
kind: implementation
title: Nightly backups and a restore applied at the next start
status: confirmed
by: claude
created: 2026-11-10T08:58:24+00:00
concerns: core/auto_backup.py, core/backup_manager.py
from: file:core/auto_backup.py, file:core/backup_manager.py
---
core/auto_backup.py makes mia_auto_<date>.zip in the backups folder once a night after 2 a.m. from the daily checks, keeps 7 nights and one a week for the 4 weeks before, never removes a hand-made backup, and stamps the day even on failure so it retries next night (the problem shows on the Backups screen). Restore from Settings now only checks the backup and keeps it opened as restore_pending.zip; apply_pending_restore runs first thing in MIAApplication.__init__, before the config or any store loads, because restoring under the running app let a store's next save write its old contents over the restored files.
