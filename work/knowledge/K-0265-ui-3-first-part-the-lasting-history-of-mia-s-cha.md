---
id: K-0265
kind: implementation
title: UI-3, first part: the lasting history of MIA's changes, and undo by time
status: confirmed
by: claude
created: 2026-11-16T10:06:05+00:00
concerns: core/change_history.py, core/undo_log.py, core/actions.py, core/assistant_actions.py, core/assistant_undo_actions.py, core/web_changes.py, web/changes.js, tests/test_change_history.py
from: dec:DEC-0188
---
What: core/change_history.py. UndoLog.add (the one place every tool's and approved action's change passes) also calls change_history.keep: one line per change in the person's history/changes.jsonl (under their profile folder; data/history without one), each line sealed on its own, with the change's id, label, summary (an action's approved sentence; a tool's name and short argument values, assistant_actions._summary_of), when, by, and per file the hash before and after; the bytes before go once per content into history/blobs/<sha256>.blob, zlib-compressed and sealed. .jsonl files and the history's own folder are skipped. Kept KEEP_DAYS (30); prune runs at a folder's first write each process. undo() goes newest first, checks every file of a change (hash now == hash right after that change, tracking hashes it restored earlier in the same pass) and restores all of them or none, then reloads stores, bumps live, records one 'undone' life event, marks the entries undone, and UndoLog.forget drops them from memory. undo_last marks its change undone in the history (mark_undone), so the two never put the same change back twice. Readers: the undo_by_time tool (lists without confirm, does it with confirm through the action history.undo), Recent Changes' Undo By Time control (core/web_changes.WHEN_CHOICES, web/changes.js).

Why this way: Opus's review measured 2.6 MB of store files changing a week, so whole files deduplicated by hash are cheap and can't be applied wrongly the way diffs can; grouping by change and restoring all-or-nothing is the review's third change; checking 'nothing changed it since' protects his own later edits instead of silently reverting them.

What went wrong: (1) two changes in the same second sorted by time alone came out oldest first, so the older looked 'changed since'; entries carry seq (write order) and sort by (at, seq). (2) A Python heredoc turned an escaped newline into a real one inside a string literal: patch scripts with backslashes go through the Write tool (memory: no backslashes through Bash). (3) 'undo what you' was a trigger phrase of undo_last_change; it now says 'undo what you just did' so 'undo what you did this afternoon' isn't claimed by both tools.

Left: reversibility and reach on every action kind (REQ-AUT-006, 007), UI-3's second part.
