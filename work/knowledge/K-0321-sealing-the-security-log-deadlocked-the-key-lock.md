---
id: K-0321
kind: lesson
title: Sealing the security log deadlocked the key lock
status: confirmed
by: claude
created: 2026-11-21T07:45:19+00:00
concerns: core/at_rest.py, core/security_log.py
from: task:WP-04
---
WP-04. at_rest._open_keys runs under at_rest._lock and, when the key won't open, notes it in the security log (_alert). Once security_log.jsonl was LINE_SEALED, record() called seal_line -> seal -> _current_key, which asked for the same non-reentrant lock on the same thread: MIA (and the suite, at test_a_key_file_that_won_t_open_is_never_replaced) hung forever. The lock is now an RLock; the inner call finds _blocked set and writes the line plain. Anything at_rest calls while holding its lock must not be assumed free of sealing.
