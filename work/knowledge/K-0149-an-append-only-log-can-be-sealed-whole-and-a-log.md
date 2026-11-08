---
id: K-0149
kind: lesson
title: An append-only log can be sealed whole; and a log of what happened must stay outside undo
status: confirmed
by: claude
created: 2026-11-08T21:08:38+00:00
concerns: core/failure_log.py, core/at_rest.py, core/undo_log.py, core/sync.py, tests/test_at_rest.py
from: dec:DEC-0126
---
DEC-0126, 2026-11-08: the earlier note said the .jsonl logs needed a per-line sealed format because phone and PC merge them line by line under different keys. Reading core/sync.py showed otherwise: sync hashes and sends each file's opened content (at_rest.open_bytes) and writes the merge back through atomic_write_text, so each device seals with its own key. So failures.jsonl became a whole-file write (read with open_text, add the line, trim, atomic_write_text) and joined SEALED with failure_state.json. What would have gone wrong: (1) a raw append to a sealed file breaks the envelope, the next read sets the file aside and the log starts empty; every writer has to go through atomic_write_text first. (2) atomic_write_text feeds 'undo that': a tool that errors inside a recorded change would have made the stumble undoable, or kept a change that touched nothing else. undo_log.outside_undo() now wraps such writes. The store also opens the log at construction so an unopenable one is set aside at sign-in like every sealed store (the parametrized at_rest test caught that).
