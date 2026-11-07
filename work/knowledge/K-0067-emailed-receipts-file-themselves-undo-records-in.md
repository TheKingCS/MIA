---
id: K-0067
kind: decision
title: Emailed receipts file themselves; undo records instead of file snapshots
status: confirmed
by: claude
created: 2026-11-07T15:05:57+00:00
concerns: core/inbox_manager.py, core/receipt_effects.py, core/inbox_actions.py
from: dec:DEC-0121
---
DEC-0121. Why not core/undo_log.py: it keeps the last 20 changes in memory and restores whole files, so undoing a receipt days later would erase everything written to those stores since. Instead each receipt effect returns an undo record of exactly what it changed and what it was before (quantity added, previous done date and mileage, the reading it logged, the previous unit cost, ids of what it created), kept on the inbox item with the expense id; InboxManager.unfile deletes the expense and reverses the records newest first, skipping any whose record is gone. auto_file runs in scan() for emailed receipts only, skipping invoices and duplicates.
What went wrong: the duplicate guard first required the same store, and a forwarded copy read its store from the forwarder, so it was filed twice; the same cents within a day now counts as the same purchase. A bash heredoc failed on quoting again: patch scripts are written with Write.
