---
id: K-0306
kind: implementation
title: Done means read back: every approved change is checked after it runs
status: confirmed
by: claude
created: 2026-11-18T15:38:59+00:00
concerns: core/read_back.py, core/record_types.py, core/actions.py, core/undo_log.py
from: commit:03b0332c, dec:DEC-0218
---
LS-05: core/read_back.check runs after an action executes. Each file the change wrote must still hold the bytes it left (undo_log.after_write keeps a sha256 as atomic_write_text finishes). Each kind:id its life events named must resolve through core/record_types.read, unless a removal event in the same change named it, or the kind isn't readable on that view. The proposal keeps read_back (ok or the problems) and the result line says so; it stays done and undoable. Watching the read-back over the whole suite found two mixed refs at once: workshop builds wrote recipe: (the kitchen's) instead of craft_recipe:, and personal record sets write record_set: (RecordType.read_also covers it). Run the suite with a pytest plugin that wraps read_back.check to see what it flags.
