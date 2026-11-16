"""
core.homeostasis
==================

MIA easing off her own background work (the Living System doctrine's homeostasis, DEC-0173, G2; Zac 2026-11-15:
"Mia should slow herself down but make a notice about it").

**What it decides** (`Homeostasis.defer_reason`): whether a *deferrable* job should wait this time. Essential jobs
(alarms, the battery, the inbox, backups, the once-a-day tick itself) never wait. Deferrable ones (`DEFERRABLE_JOBS`,
`DEFERRABLE_CHECKS`) wait while:
- the computer is busy: the processor at 85% or more on the last three readings, or less than 10% of memory free;
- it's on battery below 30%;
- it's offline, for the ones that go online (`ONLINE`);
- the disk has less than 5% free, for the ones that write a lot (`HEAVY`).
A job that waits is tried again at its next turn; nothing is lost. Readings come from `core/system_health.py`,
`core/power_manager.py` and `core/connectivity.py`, at most every 30 seconds.

**Backoff** (`backoff_seconds`, used by `core/scheduler.py`): a job that fails three runs in a row waits twice its
interval, then four times, up to six hours, until it works again. One success resets it.

**The notice:** each time she starts easing off (the conditions turn from clear to not), and each time a job starts
backing off, she says so once, through the communication gate (topic `homeostasis`), in plain words with why and
what's waiting. Nothing is said again until things have been clear and turn again. These are her own reversible
choices about her own work, logged and shown in the runtime's health (`/api/runtime/health`).

**The pages** (`easing_now`, appearance A7): while the last reading (within ten minutes) found the computer busy or the
battery low, the look sent to pages says so, and an ambient backdrop stays still.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

# The scheduler's jobs (core/background_jobs.JOBS) and daily checks (DAILY_CHECKS) that may wait.
DEFERRABLE_JOBS = frozenset({"world_intel"})
DEFERRABLE_CHECKS = frozenset({"good_news", "night_school", "dependency_audit", "system_map", "chronicle_issue",
                               "vault_captions", "seasons_of_memory"})
ONLINE = frozenset({"world_intel", "good_news", "dependency_audit", "night_school"})  # wait when offline
HEAVY = frozenset({"night_school", "vault_captions", "chronicle_issue"})  # wait when the disk is nearly full
NAMES = {"world_intel": "World Intelligence's watches", "good_news": "Good News Radio", "night_school": "Night School",
         "dependency_audit": "the dependency check", "system_map": "the system map", "chronicle_issue":
         "the Chronicle's issue", "vault_captions": "photo captions", "seasons_of_memory": "Seasons of Memory"}

BUSY_CPU = 85.0
BUSY_READINGS = 3
LOW_MEMORY = 10.0  # percent free
LOW_BATTERY = 30.0
LOW_DISK = 5.0  # percent free
READ_EVERY = 30.0  # seconds between readings
BACKOFF_AFTER = 3  # failures in a row
BACKOFF_MOST = 6 * 3600.0


EASING_FRESH = 600.0  # seconds a "busy or on battery" reading counts for the pages
_EASED_AT: Optional[float] = None  # when this process last read the machine as busy or on low battery


def easing_now() -> bool:
    """Whether MIA is easing off right now for a busy computer or a low battery, as last read in the last ten minutes
    (the pages keep their ambient backdrop still while she does: core/appearance.for_shell)."""
    return _EASED_AT is not None and time.monotonic() - _EASED_AT < EASING_FRESH


def backoff_seconds(interval: float, failures_in_a_row: int) -> float:
    """Pure logic. How long a job waits before its next try: its interval until it has failed BACKOFF_AFTER times
    in a row, then twice, four times... its interval, never more than six hours (nor less than its interval)."""
    if failures_in_a_row < BACKOFF_AFTER:
        return interval
    return max(interval, min(BACKOFF_MOST, interval * 2 ** (failures_in_a_row - BACKOFF_AFTER + 1)))


def conditions(cpu: list, memory_free: Optional[float], battery: Optional[tuple], online: Optional[bool],
               disk_free: Optional[float]) -> dict:
    """Pure logic. What isn't clear right now, as {condition: why}: busy, battery, offline, disk. `cpu` is the
    recent processor readings (newest last), `battery` (percent, plugged in) or None, `online` None when unknown."""
    found = {}
    recent = list(cpu)[-BUSY_READINGS:]
    if len(recent) == BUSY_READINGS and all(c >= BUSY_CPU for c in recent):
        found["busy"] = f"the computer is busy (processor at {recent[-1]:.0f}%)"
    elif memory_free is not None and memory_free < LOW_MEMORY:
        found["busy"] = f"the computer is low on memory ({memory_free:.0f}% free)"
    if battery is not None and not battery[1] and battery[0] < LOW_BATTERY:
        found["battery"] = f"the battery is at {battery[0]:.0f}% and not charging"
    if online is False:
        found["offline"] = "there's no internet connection"
    if disk_free is not None and disk_free < LOW_DISK:
        found["disk"] = f"the disk is nearly full ({disk_free:.0f}% free)"
    return found


def reason_for(name: str, found: dict) -> str:
    """Pure logic. Why this job waits under these conditions, or "" when it may run. Busy and battery hold every
    deferrable job; offline holds the online ones; a full disk holds the heavy ones."""
    if name not in DEFERRABLE_JOBS and name not in DEFERRABLE_CHECKS:
        return ""
    for key in ("busy", "battery"):
        if key in found:
            return found[key]
    if "offline" in found and name in ONLINE:
        return found["offline"]
    if "disk" in found and name in HEAVY:
        return found["disk"]
    return ""


class Homeostasis:
    """One MIA's easing off: reads the machine (at most every 30 seconds), decides which deferrable work waits, and
    says so once each time she starts easing off or a job starts backing off."""

    def __init__(self, context, read: Optional[Callable[[], dict]] = None, clock: Callable[[], float] = time.monotonic):
        """`read` returns {cpu, memory_free, battery, online, disk_free} (the real machine by default; tests pass
        their own)."""
        self.context = context
        self._read = read or self._read_machine
        self._clock = clock
        self._cpu: deque = deque(maxlen=BUSY_READINGS)
        self._last_read = -READ_EVERY
        self.found: dict = {}
        self.waiting: dict = {}  # job or check -> why, this episode
        self.deferrals = 0
        self._noticed = False  # said so for this episode already

    def _read_machine(self) -> dict:
        """The real readings: processor, memory and disk from psutil, the battery, the connection. None of them in a
        test run (a busy machine running the suite would make tests skip work at random); tests pass `read`."""
        import os

        out = {"cpu": None, "memory_free": None, "battery": None, "online": None, "disk_free": None}
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return out
        try:
            import psutil

            from core.data_root import HOME

            out["cpu"] = psutil.cpu_percent(interval=None)
            out["memory_free"] = psutil.virtual_memory().available * 100.0 / psutil.virtual_memory().total
            disk = psutil.disk_usage(str(HOME))
            out["disk_free"] = disk.free * 100.0 / disk.total
        except Exception:  # noqa: BLE001 - a phone or a machine psutil can't read: no reading, no deferral
            pass
        power = getattr(self.context, "power", None)
        try:
            status = power.read() if power is not None else None
            if status is not None:
                out["battery"] = (float(status.percent), bool(status.plugged_in))
        except Exception:  # noqa: BLE001
            pass
        monitor = getattr(self.context, "connectivity", None)
        try:
            from core.connectivity import OFFLINE, ONLINE as UP

            state = getattr(monitor, "status", "") if monitor is not None else ""
            out["online"] = True if state == UP else False if state == OFFLINE else None
        except Exception:  # noqa: BLE001
            pass
        return out

    def refresh(self) -> dict:
        """Reads the machine when the last reading is older than 30 seconds; notes for the pages whether she's easing
        off for a busy computer or a low battery (`easing_now`); ends an episode (and its notice) once everything is
        clear. Returns what isn't clear."""
        now = self._clock()
        if now - self._last_read >= READ_EVERY:
            self._last_read = now
            r = self._read()
            if r.get("cpu") is not None:
                self._cpu.append(float(r["cpu"]))
            self.found = conditions(list(self._cpu), r.get("memory_free"), r.get("battery"), r.get("online"),
                                    r.get("disk_free"))
            global _EASED_AT
            _EASED_AT = time.monotonic() if ("busy" in self.found or "battery" in self.found) else None
            if not self.found:
                self.waiting, self._noticed = {}, False
        return self.found

    def defer_reason(self, name: str) -> str:
        """Why this job or daily check waits now, or "" to run it. A wait is counted, remembered for the notice and
        the health report, and the first of an episode is said once."""
        why = reason_for(name, self.refresh())
        if why:
            self.deferrals += 1
            self.waiting[name] = why
            if not self._noticed:
                self._noticed = True
                self._notice(why)
        return why

    def _notice(self, why: str) -> None:
        """Says once that she's easing off, why, and what waits (through the gate)."""
        names = sorted({NAMES.get(n, n.replace("_", " ")) for n in self.waiting})
        self._offer("easing_off", "Easing off for now",
                    f"{why[0].upper()}{why[1:]}, so {', '.join(names)} will wait until it's clear. Nothing is lost.")

    def backing_off(self, name: str, failures: int, wait_seconds: float, error: str) -> None:
        """Says once that a job has failed several times in a row and will be tried less often (from the scheduler), and
        her orb shows a warning for a moment (core/orb_state.py)."""
        from core import orb_state

        orb_state.flash("warning")
        hours = wait_seconds / 3600
        when = f"every {hours:.0f} hours" if hours >= 1 else f"every {wait_seconds / 60:.0f} minutes"
        label = NAMES.get(name, name.replace("_", " "))
        self._offer(f"backoff_{name}", f"Slowing down {label}",
                    f"It failed {failures} times in a row ({error[:120] or 'no reason given'}), so I'll try {when} "
                    f"instead of retrying constantly. It goes back to normal as soon as it works.")

    def _offer(self, key: str, title: str, message: str) -> None:
        """One notice through the communication gate (logged); quietly logged only when there's no gate."""
        log.info("Homeostasis: %s: %s", title, message)
        gate = getattr(self.context, "communication", None)
        if gate is None:
            return
        try:
            from core.communication_gate import TIMELY, Candidate

            gate.offer(Candidate(topic="homeostasis", title=title, message=message, urgency=TIMELY,
                                 source="system", fingerprint=f"{key}|{message}"))
        except Exception:  # noqa: BLE001 - a notice that can't be offered never stops the schedule
            log.exception("Couldn't offer the homeostasis notice")

    def report(self) -> dict:
        """For the runtime's health: what isn't clear, what's waiting and why, and how many waits so far."""
        return {"conditions": dict(self.found), "waiting": dict(self.waiting), "deferrals": self.deferrals}
