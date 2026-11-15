"""
core.scheduler
================

MIA's background schedule, without Qt (the MIA Runtime, DEC-0155; step 2 of
`docs/mia_os/preliminary/MIA_OS_INITIAL_IMPLEMENTATION_PLAN.md`).

What it is: a list of named jobs, each run every so many seconds. It
replaces the ten `QTimer`s the desktop window owned, so the same schedule
runs with or without a window: on the desktop, in a headless service on
MIA OS or the Pi, and in tests.

How it works:
- **It is passive.** `run_due()` runs the jobs that are due now and
  returns. Something else calls it: the desktop a single `QTimer` on its
  own thread (so jobs still run where they always did); a headless runtime
  `run_forever()` on a thread. The clock is passed in, so tests don't wait.
- **One at a time, never overlapping.** `run_due()` runs jobs one after
  another on the caller's thread; a second caller while one is running
  gets nothing to do.
- **Under the store lock, or not now.** With a lock given, a job runs only
  if the lock is free this instant (the phone's server may be mid-request).
  A job that couldn't run stays due and is tried at the next `run_due()`,
  counted as a skip. The schedule never waits on the lock.
- **A job that fails is logged and keeps its place.** Its error is kept in
  its status; the other jobs still run.
- **No catching up.** After a long sleep a job runs once, not once for
  every interval it missed.

`status()` is what `/api/health` and Diagnostics show: each job's interval,
last run, how long it took, runs, skips and its last error.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)


@dataclass
class Job:
    """One scheduled job: its name, how often it runs (seconds), what it calls, when it's next due (on the
    scheduler's clock), and its record: runs, skips (the stores were busy), failures, the last run's time (wall
    clock, ISO) and length, and the last error in words."""
    name: str
    seconds: float
    run: Callable[[], None]
    due: float
    runs: int = 0
    skips: int = 0
    failures: int = 0
    last_run: str = ""
    last_seconds: float = 0.0
    last_error: str = ""


class Scheduler:
    """Named jobs on intervals, run by whoever calls `run_due()` (see the module's opening)."""

    def __init__(self, clock: Callable[[], float] = time.monotonic, lock=None,
                 wall: Optional[Callable[[], str]] = None) -> None:
        """`clock` counts seconds (monotonic by default; a fake one in tests). `lock` is the store lock jobs run
        under, or None. `wall` gives the time written in a job's record."""
        from datetime import datetime

        self._clock = clock
        self._lock = lock
        self._wall = wall or (lambda: datetime.now().isoformat(timespec="seconds"))
        self._jobs: dict[str, Job] = {}
        self._running = threading.Lock()  # held while run_due is running jobs

    def add(self, name: str, seconds: float, run: Callable[[], None], first_after: Optional[float] = None) -> Job:
        """Adds a job run every `seconds`. Its first run is one interval from now, as a timer's would be, unless
        `first_after` says sooner (0: at the next `run_due()`). ValueError for a name used twice or an interval
        that isn't positive."""
        if name in self._jobs:
            raise ValueError(f"There's already a job called {name}.")
        if seconds <= 0:
            raise ValueError("A job's interval is more than zero seconds.")
        job = Job(name, float(seconds), run, self._clock() + (seconds if first_after is None else first_after))
        self._jobs[name] = job
        return job

    def names(self) -> list[str]:
        """The jobs' names, in the order they were added."""
        return list(self._jobs)

    def run_due(self) -> list[str]:
        """Runs every job that's due now, in the order they were added, and returns the names that ran. A job whose
        turn comes while the stores are busy stays due. Returns [] at once when another call is still running
        jobs."""
        if not self._running.acquire(blocking=False):
            return []
        try:
            ran = []
            for job in list(self._jobs.values()):
                if self._clock() < job.due:
                    continue
                if self._run(job):
                    ran.append(job.name)
            return ran
        finally:
            self._running.release()

    def _run(self, job: Job) -> bool:
        """Runs one due job under the store lock; False when the stores were busy (it stays due). A failure is
        logged and recorded, and the job is due again one interval on, like a run that worked."""
        if self._lock is not None and not self._lock.acquire(blocking=False):
            job.skips += 1
            log.debug("Skipped %s for now: the stores are busy.", job.name)
            return False
        started = self._clock()
        try:
            job.run()
            job.last_error = ""
        except Exception as problem:  # noqa: BLE001 - one job's failure never stops the schedule
            job.failures += 1
            job.last_error = f"{type(problem).__name__}: {problem}"[:300]
            log.exception("The scheduled job '%s' failed; the others still run.", job.name)
        finally:
            if self._lock is not None:
                self._lock.release()
        finished = self._clock()
        job.runs += 1
        job.last_run = self._wall()
        job.last_seconds = round(finished - started, 3)
        job.due = finished + job.seconds  # from when it finished: no catching up after a sleep or a long run
        return True

    def next_wait(self, most: float = 5.0) -> float:
        """Seconds until the next job is due (0 when one already is), at most `most`."""
        if not self._jobs:
            return most
        return max(0.0, min(most, min(j.due for j in self._jobs.values()) - self._clock()))

    def run_forever(self, stop: threading.Event, most: float = 5.0) -> None:
        """Runs due jobs until `stop` is set, sleeping until the next is due (at most `most` seconds, so a stop or
        a job that was skipped is picked up soon). For a headless runtime's thread."""
        while not stop.is_set():
            self.run_due()
            stop.wait(max(0.2, self.next_wait(most)))

    def status(self) -> list[dict]:
        """Each job's record, for /api/health and Diagnostics: name, interval, runs, skips, failures, the last run's
        time and length, the last error, and the seconds until it's next due."""
        now = self._clock()
        return [{"name": j.name, "every_seconds": j.seconds, "runs": j.runs, "skips": j.skips, "failures": j.failures,
                 "last_run": j.last_run, "last_seconds": j.last_seconds, "last_error": j.last_error,
                 "due_in_seconds": round(max(0.0, j.due - now), 1)} for j in self._jobs.values()]
