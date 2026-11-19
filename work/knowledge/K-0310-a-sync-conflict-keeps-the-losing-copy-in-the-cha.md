---
id: K-0310
kind: implementation
title: A sync conflict keeps the losing copy in the change history, with one note
status: confirmed
by: claude
created: 2026-11-19T02:56:37+00:00
concerns: core/sync.py, core/change_history.py
from: commit:8686ff0a, dec:DEC-0285
---
LS-03 (DEC-0285): merge_json and _merge_list carry a path (keys and id=... steps); inside sync.conflicts() a field both sides changed since the base is noted. sync_now then calls keep_loser(): the losing side's copy of the whole file goes into change_history as a Change labelled sync_conflict (by='sync'), so undo by time brings it back for 30 days, and conflict_note() names the file and field paths, never a value.
