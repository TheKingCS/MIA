---
id: K-0328
kind: implementation
title: The restore drill and the second copy off the PC
status: confirmed
by: claude
created: 2026-11-22T13:40:30+00:00
concerns: core/restore_drill.py, core/auto_backup.py, core/web_backups.py
from: task:WP-09, dec:DEC-0259
---
WP-09 (DEC-0259, REQ-SEC-037). core/restore_drill.py: monthly from 3 a.m. (EVERY_DAYS 28), the newest mia_auto_ zip (else the newest plain zip; a passphrase .miabackup can't be opened at night) is extracted with backup_manager.safe_extract_zip into a mkdtemp scratch folder and every data/*.json and *.jsonl opened the way MIA does (unseal or open_lines, then json); the folder is always removed. The result is the config's backup.drill; a failure is a direct notification (always=True). auto_backup.copy_offsite copies the night's zip to backup.offsite_folder through a .partial name then replace, and rotates it with keep(), which now also keeps 6 monthlies (none older than about 7+28+186 days). A drive not there (its anchor missing) is backup.offsite_problem, never a failed backup. Daily check restore_drill; loop decision none (pass or fail, no judgement of hers).
