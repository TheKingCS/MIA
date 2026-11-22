---
id: K-0337
kind: implementation
title: A phone paired again starts sync fresh
status: confirmed
by: claude
created: 2026-11-22T15:29:21+00:00
concerns: core/sync.py, core/home_link.py
from: task:FW-07b
---
FW-07b (REQ-IMP-005). home_link.connect calls sync.start_fresh after linking: the state's last-synced copies (each scope's folder, files.json, game.json) are removed and status fresh=True. In sync_now, while fresh, a file both sides have and that differs is pulled and written (the computer's moved copy), and the phone's copy is kept with keep_loser(..., note=fresh_note(name)) in its change history for 30 days; a file only the phone has still goes up; fresh=False once a whole sync is done. Without it, a base of None made the phone's newer-mtime copy win the merge over moved data.
