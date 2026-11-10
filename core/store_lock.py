"""
core.store_lock
=================

The lock the server holds while a request reads or changes MIA's stores,
let go of while the model thinks (roadmap 2.3, 2026-11-10).

Before: `server/app.py` held one plain lock for a whole turn, the model
call included, so while MIA thought (seconds, up to a minute) every other
request from the phone, the glasses and the web pages waited. Now:

- `StoreLock` is that lock, knowing which thread holds it.
- `released()` lets go of every StoreLock the calling thread holds, for a
  block that touches no store, and takes them back after, in the order
  they were taken. `core/llm_manager.LLMManager._ask` wraps each model
  call in it, so the slow part of a turn holds nothing. Anywhere without
  a StoreLock held (the desktop's worker threads, tools, tests) it does
  nothing.
- `conversation_lock(key)`: one lock per conversation, taken before the
  store lock, so one conversation's turns still run one after another
  even while the store lock is let go mid-turn.

What a turn read before the model call is still in memory after it, and
what changed meanwhile is visible too: stores are shared objects, and
the tools a reply calls run after the lock is taken back.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager

_local = threading.local()


def _held() -> list:
    """The StoreLocks this thread holds, in the order it took them."""
    if not hasattr(_local, "held"):
        _local.held = []
    return _local.held


class StoreLock:
    """A plain (non-reentrant) lock that remembers it's held by this thread, so released() can let it go and take it
    back. Same calls as threading.Lock: acquire, release, locked, and `with`."""

    def __init__(self) -> None:
        """Starts unheld."""
        self._lock = threading.Lock()

    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
        """Takes the lock (waiting, or up to `timeout` seconds); True when taken."""
        taken = self._lock.acquire(blocking, timeout)
        if taken:
            _held().append(self)
        return taken

    def release(self) -> None:
        """Lets the lock go."""
        held = _held()
        for i in range(len(held) - 1, -1, -1):
            if held[i] is self:
                del held[i]
                break
        self._lock.release()

    def locked(self) -> bool:
        """Whether some thread holds it."""
        return self._lock.locked()

    def __enter__(self) -> "StoreLock":
        """`with lock:` takes it."""
        self.acquire()
        return self

    def __exit__(self, *exc) -> None:
        """...and lets it go."""
        self.release()


@contextmanager
def released():
    """Lets go of every StoreLock this thread holds for the block (the model thinking), then takes them back in the
    order they were first taken. Does nothing when none is held."""
    held = list(_held())
    for lock in reversed(held):
        lock.release()
    try:
        yield
    finally:
        for lock in held:
            lock.acquire()


_conversation_locks: dict = {}
_guard = threading.Lock()


def conversation_lock(key) -> threading.Lock:
    """The lock for one conversation (by its id): its turns run one at a time, in the order they came."""
    with _guard:
        lock = _conversation_locks.get(key)
        if lock is None:
            lock = _conversation_locks[key] = threading.Lock()
        return lock
