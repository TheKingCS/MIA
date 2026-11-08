---
id: K-0082
kind: implementation
title: Recent Changes: the undo history on a page, Undo as an action
status: confirmed
by: claude
created: 2026-11-08T00:44:10+00:00
concerns: core/web_changes.py, web/changes.js, core/undo_log.py
from: dec:DEC-0125
---
The screens review listed 'Recent changes / Undo history' as missing; 'undo that' and 'what did you just change?' were voice-only. web/changes.html (linked from Settings) shows core/web_changes.changes_page: the undo log's changes for this person, newest first, each in the history's own summary when the change recorded life events (else its action's label), when and by whom; and the last 14 days of the history by day, undone events struck through. Undo is the action undo.last, newest first like the voice. Gotcha: an action's execute runs inside undo_log.recording(), and undo_last writes a history event through atomic_write, so the undo would itself become an undoable change (undoing it would only drop that event). _undo wraps undo_last in its own nested recording('undo', None), whose files are thrown away, so nothing new reaches the log; tests/test_web_changes.py checks the log is empty after.
