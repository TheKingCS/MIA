"""
core.deadline
=============

A deadline and the stop, for device and outside work only (DEC-0283, LS-04,
docs/mia_os/MIA_UNIVERSAL_RUNTIME_CONTRACTS.md section 2). A long loop that waits on something outside MIA (a browser
task, a download) asks `why_not()` between its steps, never in the middle of a write: it says why the loop should end
now, "everything is stopped" when a stop-everything is in force (core/stop.py), or that the work ran past its time;
"" while it may carry on. `check()` raises the same as an action error of the matching kind (`Refused` for the stop,
`Unavailable` for the time). Record changes get no deadline: they are fast and local, and synchronous Python can't
safely be cut off mid-write.
"""

from __future__ import annotations

import time
from typing import Callable


class Deadline:
    """How long one piece of outside work may take (`seconds`), what it is (`what`, for the words), and the clock."""

    def __init__(self, seconds: float, what: str, clock: Callable[[], float] = time.monotonic,
                 stopped: Callable[[], bool] = None) -> None:
        """Starts the time now; `stopped` says whether everything is stopped (core/stop.held_now by default)."""
        self.seconds, self.what, self._clock = float(seconds), what, clock
        self._end = clock() + self.seconds
        self._stopped = stopped

    def _is_stopped(self) -> bool:
        """Whether a stop-everything is in force; a stop that can't be read is no stop."""
        if self._stopped is not None:
            return bool(self._stopped())
        try:
            from core import stop

            return stop.held_now()
        except Exception:  # noqa: BLE001 - reading the stop never breaks the work
            return False

    def why_not(self) -> str:
        """Why the work should end now, in words; "" while it may carry on. The stop comes first."""
        if self._is_stopped():
            return "everything is stopped"
        if self._clock() >= self._end:
            return f"{self.what} took longer than {int(self.seconds)} seconds"
        return ""

    def check(self) -> None:
        """Raises `Refused` (the stop) or `Unavailable` (out of time) when the work should end; else nothing."""
        why = self.why_not()
        if not why:
            return
        from core.actions import Refused, Unavailable

        raise (Refused if why == "everything is stopped" else Unavailable)(why[0].upper() + why[1:] + ".")
