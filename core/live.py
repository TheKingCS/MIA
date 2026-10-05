"""
core.live
===========

Live updates (2026-10-05, Phase 2 foundation, DEC-0013): one number,
the state version, that goes up whenever any of MIA's data changes, so
every open surface (the web Home, the phone, later the glasses) knows to
re-read `/api/state` the moment something changes, wherever it changed:
the desktop, the phone, the Assistant, an import, an undo.

Bumped by `core.atomic_write.atomic_write_text` (nearly every store's
save), `core.life_events.record` and `core.undo_log.undo_last`. Served
by `/api/live` (a stream) and `/api/live/version` (one read). The
number restarts at 0 when MIA starts; surfaces compare it, never store
it. Thread-safe: the phone server runs on its own thread.
"""

from __future__ import annotations

import threading
import time

_lock = threading.Lock()
_version = 0
_changed_at = 0.0


def bump() -> int:
    global _version, _changed_at
    with _lock:
        _version += 1
        _changed_at = time.time()
        return _version


def version() -> int:
    with _lock:
        return _version


def changed_at() -> float:
    with _lock:
        return _changed_at
