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

- **Conditions**, true for as long as they're true: `needs-you` while a card waits for a yes (`watch`: asked of
  core/actions.py's ActionCenter whenever the state is read, so a card decided or expired stops counting at
  once); `offline` (`hold(state, on)`) while answers in words aren't ready, because the
  model server doesn't answer (`core/llm_manager.py`: its reachability check, or a turn that couldn't reach it;
  cleared by the next answer). DEC-0255: "her orb says when answers in words aren't ready yet".
  `held(state)` says whether one is held (the capability registry reads `offline`: WP-08).

**What she's doing** (`doing(words)`, a context manager around one lookup in a turn, core/tool_loop.py): a few words
from the tool really running ("Reading your library", "Checking your money"), sent with the state as its `detail`
(brainstorm 1.1: he knows what the wait is for); the page shows "Thinking · Reading your library". Never invented:
only while that tool runs.

`current()` is the strongest one now, in `PRIORITY` order, else `idle`. `listening` and `speaking` are the page's own
(only the device knows its microphone is open or its speaker playing), so the page shows them itself.

**Each state's look** (`LOOK`, WP-07, REQ-VIS-009/010): its words (the orb's label, and what a screen reader says)
and a still glyph, shown instead of the motion when the device asks for reduced motion. Pages take them from the
frame's data (`look()`, /api/shell), so every orb says the same.

Pages learn of a change through the live stream (`/api/live`, a `presence` event) without re-reading any data:
`version()` moves only when the state does. Thread-safe: the phone server and the scheduler run on their own threads.
"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Callable, Optional

# Strongest first (the orb spec, MIA_OS_ORB_VISUAL_AND_BEHAVIOR_SPECIFICATION.md section 1: a card waiting outranks
# everything she does; being offline shows only when nothing else does).
PRIORITY = ("needs-you", "council", "working", "thinking", "warning", "success", "notification", "offline")
ACTIVITIES = ("thinking", "working", "council")
MOMENTS = ("success", "warning", "notification")
CONDITIONS = ("offline", "needs-you")
PAGE_STATES = ("listening", "speaking")  # the device's own: its microphone, its speaker
# Every state the orb shows: (its words, a still glyph for reduced motion). Each glyph is its own (a test checks).
LOOK = {
    "idle": ("Here", "\u25cb"),
    "listening": ("Listening", "\u25ce"),
    "speaking": ("Speaking", "\u266a"),
    "thinking": ("Thinking", "\u2026"),
    "working": ("Working on it", "\u2699"),
    "council": ("Asking the council", "\u2042"),
    "notification": ("A message for you", "\u2709"),
    "warning": ("Something needs a look", "!"),
    "success": ("Done", "\u2713"),
    "needs-you": ("Needs you: a card is waiting", "\u25c6"),
    "offline": ("Offline: answers in words aren't ready yet", "\u25cc"),
}
FLASH_SECONDS = 4.0

_lock = threading.Lock()
_active: dict = {}  # activity -> how many are running
_flashes: dict = {}  # moment -> until (clock seconds)
_held: set = set()  # conditions true now
_doing: list = []  # what she's doing right now, innermost last (`doing`)
_probes: dict = {}  # condition -> a callable that says whether it's true now
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


@contextmanager
def doing(words: str):
    """Says what she's doing (a few words) for the length of the `with` block; nested ones stack, the newest shown."""
    words = " ".join(str(words or "").split())[:60]
    with _lock:
        _doing.append(words)
        _changed()
    try:
        yield
    finally:
        with _lock:
            if words in _doing:
                _doing.reverse()
                _doing.remove(words)
                _doing.reverse()
            _changed()


def detail() -> str:
    """What she's doing right now, in a few words ("" when nothing is said)."""
    with _lock:
        return _doing[-1] if _doing else ""


def flash(state: str, seconds: float = FLASH_SECONDS) -> None:
    """Shows a moment for a few seconds. Never raises (a moment never breaks the work it reports)."""
    if state not in MOMENTS:
        return
    with _lock:
        _flashes[state] = _clock() + seconds
        _changed()


def hold(state: str, on: bool) -> None:
    """Holds a condition on or off (only a change moves the version). Never raises for a state that isn't one: it's
    ignored, as a condition never breaks what reports it."""
    if state not in CONDITIONS:
        return
    with _lock:
        if (state in _held) == bool(on):
            return
        (_held.add if on else _held.discard)(state)
        _changed()


def watch(state: str, probe: Callable[[], bool]) -> None:
    """A condition that's true whenever `probe()` says so, asked each time the state is read (outside this module's
    lock); one that raises counts as false. A state that isn't a condition is ignored."""
    if state in CONDITIONS:
        with _lock:
            _probes[state] = probe
            _changed()


def _probed() -> set:
    """The watched conditions true now (each probe asked outside the lock, never raising)."""
    with _lock:
        probes = list(_probes.items())
    out = set()
    for state, probe in probes:
        try:
            if probe():
                out.add(state)
        except Exception:  # noqa: BLE001 - a probe that fails says nothing
            continue
    return out


def held(state: str) -> bool:
    """Whether a condition is held now (`hold`; a watched one isn't asked here)."""
    with _lock:
        return state in _held


def look() -> dict:
    """Pure logic. Every state's words and still glyph, for the pages: {state: {label, glyph}}."""
    return {state: {"label": label, "glyph": glyph} for state, (label, glyph) in LOOK.items()}


def current(now: Optional[float] = None) -> str:
    """The strongest state now (`PRIORITY`), else idle. A moment that has passed stops counting; a condition counts
    while it's held."""
    now = _clock() if now is None else now
    watched = _probed()
    with _lock:
        live = {s for s, n in _active.items() if n > 0} | {s for s, until in _flashes.items() if until > now} | _held
    live |= watched
    return next((s for s in PRIORITY if s in live), "idle")


def version() -> int:
    """Moves whenever an activity starts or ends or a moment is shown; the live stream sends `current()` then. A
    moment's end isn't an event: the stream also re-checks `current()` every tick and sends it when it differs."""
    with _lock:
        return _version


def reset() -> None:
    """Back to idle with nothing running, held or said to be doing (tests)."""
    global _version
    with _lock:
        _active.clear()
        _flashes.clear()
        _held.clear()
        _probes.clear()
        _doing.clear()
        _version += 1
