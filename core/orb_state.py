"""
core.orb_state
================

What MIA is really doing right now, for her orb (not to be confused with `core/presence.py`, the
"what matters now" list, DEC-0044) (prompt 24 A5, DEC-0184 §8: "these states should communicate actual
system activity rather than simulate activity that is not occurring"). One state for the whole runtime, from real
events only:

- **Activities** (`active(state)`, a context manager around the work itself): `thinking` while a model is answering
  (`core/llm_manager.py`), `working` while an approved action runs (`core/actions.py`), `council` while a council
  member answers (`core/council.py`). Several can overlap; each is counted.
- **Moments** (`flash(state)`, shown for a few seconds): `success` when an action completes, `warning` when one fails or
  a job starts backing off (`core/homeostasis.py`), `notification` when the communication gate delivers a message.

`current()` is the strongest one now, in `PRIORITY` order, else `idle`. `listening` and `speaking` are the page's own
(only the device knows its microphone is open or its speaker playing), so the page shows them itself.

Pages learn of a change through the live stream (`/api/live`, a `presence` event) without re-reading any data:
`version()` moves only when the state does. Thread-safe: the phone server and the scheduler run on their own threads.
"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Callable, Optional

PRIORITY = ("council", "working", "thinking", "warning", "success", "notification")  # strongest first
ACTIVITIES = ("thinking", "working", "council")
MOMENTS = ("success", "warning", "notification")
FLASH_SECONDS = 4.0

_lock = threading.Lock()
_active: dict = {}  # activity -> how many are running
_flashes: dict = {}  # moment -> until (clock seconds)
_version = 0
_clock: Callable[[], float] = time.monotonic


def _changed() -> None:
    """Moves the version (held lock)."""
    global _version
    _version += 1


@contextmanager
def active(state: str):
    """Marks an activity as running for the length of the `with` block. ValueError for a state that isn't one."""
    if state not in ACTIVITIES:
        raise ValueError(f"{state} isn't an activity.")
    with _lock:
        _active[state] = _active.get(state, 0) + 1
        _changed()
    try:
        yield
    finally:
        with _lock:
            _active[state] = max(0, _active.get(state, 1) - 1)
            _changed()


def flash(state: str, seconds: float = FLASH_SECONDS) -> None:
    """Shows a moment for a few seconds. Never raises (a moment never breaks the work it reports)."""
    if state not in MOMENTS:
        return
    with _lock:
        _flashes[state] = _clock() + seconds
        _changed()


def current(now: Optional[float] = None) -> str:
    """The strongest state now (`PRIORITY`), else idle. A moment that has passed stops counting."""
    now = _clock() if now is None else now
    with _lock:
        live = {s for s, n in _active.items() if n > 0} | {s for s, until in _flashes.items() if until > now}
    return next((s for s in PRIORITY if s in live), "idle")


def version() -> int:
    """Moves whenever an activity starts or ends or a moment is shown; the live stream sends `current()` then. A
    moment's end isn't an event: the stream also re-checks `current()` every tick and sends it when it differs."""
    with _lock:
        return _version


def reset() -> None:
    """Back to idle with nothing running (tests)."""
    global _version
    with _lock:
        _active.clear()
        _flashes.clear()
        _version += 1
