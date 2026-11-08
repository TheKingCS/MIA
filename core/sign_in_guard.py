"""
core.sign_in_guard
====================

Sign-in protection for MIA's server (2026-11-08, Zac: "fortify our security
measures to industry standards and beyond"; docs/SECURITY.md). Two rules,
both from OWASP's authentication and session guidance:

- **Guessing a password is slow.** `SignInGuard` counts failed sign-ins
  (by the account named and by the device it came from). The first
  FREE_TRIES in WINDOW_SECONDS cost nothing; after that each try waits
  twice as long as the last (BASE_WAIT up to MAX_WAIT) before another is
  even checked. A success clears the account's count. Kept in memory: a
  restart forgives, which a person locked out by mistake may need.
- **Sessions end.** A session signed in from another device ends after
  IDLE_SECONDS unused or MAX_AGE_SECONDS in all (`session_expired`); the
  desktop's own window, signed in by the PC's session, isn't one of these,
  and neither is a linked phone's device key (core/home_link.py), which
  lasts until it's unlinked.

Nothing here logs a password or the name tried beyond the account's id.
"""

from __future__ import annotations

import threading
import time
from typing import Iterable, Optional

FREE_TRIES = 5
WINDOW_SECONDS = 15 * 60
BASE_WAIT = 30
MAX_WAIT = 15 * 60
IDLE_SECONDS = 30 * 24 * 3600
MAX_AGE_SECONDS = 90 * 24 * 3600


def wait_for(failures: int) -> int:
    """Pure logic. Seconds to wait after this many recent failures: none for the first FREE_TRIES, then BASE_WAIT,
    doubling each time, at most MAX_WAIT."""
    if failures < FREE_TRIES:
        return 0
    return min(MAX_WAIT, BASE_WAIT * 2 ** (failures - FREE_TRIES))


def session_expired(started: Optional[float], last_seen: Optional[float], now: float) -> bool:
    """Pure logic. Whether a signed-in session has ended: unused longer than IDLE_SECONDS, or older than
    MAX_AGE_SECONDS. A session without a start time (the desktop's own) never ends this way."""
    if started is None:
        return False
    return now - (last_seen or started) > IDLE_SECONDS or now - started > MAX_AGE_SECONDS


class SignInGuard:
    """Failed sign-ins per key ("who:<account>", "from:<device>"), and how long each must wait; thread-safe."""

    def __init__(self) -> None:
        """No failures yet."""
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> list[float]:
        """A key's failures within WINDOW_SECONDS (older ones dropped)."""
        kept = [t for t in self._failures.get(key, []) if now - t <= WINDOW_SECONDS]
        if kept:
            self._failures[key] = kept
        else:
            self._failures.pop(key, None)
        return kept

    def wait_left(self, keys: Iterable[str], now: Optional[float] = None) -> int:
        """Seconds before another try may be checked, the longest of the keys'; 0 when it may go ahead."""
        now = time.time() if now is None else now
        with self._lock:
            left = 0
            for key in keys:
                recent = self._recent(key, now)
                if recent:
                    left = max(left, int(wait_for(len(recent)) - (now - recent[-1]) + 0.999))
            return max(0, left)

    def failed(self, keys: Iterable[str], now: Optional[float] = None) -> None:
        """Counts a failed sign-in against each key."""
        now = time.time() if now is None else now
        with self._lock:
            for key in keys:
                self._failures.setdefault(key, []).append(now)

    def succeeded(self, keys: Iterable[str]) -> None:
        """Clears the keys' failures (the account signed in)."""
        with self._lock:
            for key in keys:
                self._failures.pop(key, None)
