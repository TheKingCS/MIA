"""
core.instance_lock
====================

One MIA per data folder (roadmap 2.4, 2026-11-10). Two copies of MIA on
the same `data/` (a double-click while one is already running, the
desktop and `core_main.py` at once) each keep their own stores in memory
and save over each other's changes. Nothing stopped it.

`acquire(path)` takes an operating-system lock on `data/.mia.lock` and
keeps the file open for the life of the process; the lock goes with the
process, even when it crashes, so there's nothing stale to clean up. A
second process gets False and says so instead of starting. Asking again
in the same process is True (tests build the app many times).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

PATH = Path(__file__).resolve().parent.parent / "data" / ".mia.lock"
_held: dict[str, object] = {}


def acquire(path: Optional[Path] = None) -> bool:
    """Takes the lock for this data folder; False when another running MIA holds it. A folder that can't be written
    (a read-only disk) doesn't stop MIA: it's logged and counts as taken."""
    path = Path(path or PATH)
    key = str(path.resolve())
    if key in _held:
        return True
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(path, "a+b")
    except OSError:
        log.exception("Couldn't open %s; starting without the one-MIA check", path)
        return True
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return False
    _held[key] = handle
    return True


def release(path: Optional[Path] = None) -> None:
    """Lets the lock go (tests; a process's own lock goes when it ends)."""
    key = str(Path(path or PATH).resolve())
    handle = _held.pop(key, None)
    if handle is None:
        return
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    except OSError:
        pass
    handle.close()
