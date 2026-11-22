"""
core.model_queue
==================

One model job at a time on this computer's GPU, the conversation first (FW-12, DEC-0204: "MIA keeps one model job per
GPU at a time, conversation first, then specialists, the Workroom, background work"; REQ-HW-029: "a conversation
he's in shall never wait behind background model work for more than one model load").

Every call to her local model goes through `slot()` (core/llm_manager.py `_ask`). A slot is taken by the strongest
kind waiting (`KINDS`, strongest first), the earliest of a kind first; one call at a time. So a turn of his waits at
most for the one call already running, never for a line of background ones queued before it.

A call's kind is its thread's: a conversation unless marked. Her schedule marks its jobs `background` (`as_kind`,
core/scheduler.py), a specialist or the Workroom may mark theirs. A thread that already holds the slot passes
straight through (a call made from inside another never waits on itself). Thread-safe.
"""

from __future__ import annotations

import itertools
import threading
from contextlib import contextmanager
from typing import Optional

KINDS = ("conversation", "specialist", "workroom", "background")  # strongest first (DEC-0204)

_cond = threading.Condition()
_waiting: list = []  # (rank, ticket number) of each call waiting for the slot
_holder: Optional[int] = None  # the thread holding the slot
_held_kind = ""
_tickets = itertools.count()
_local = threading.local()


def current_kind() -> str:
    """This thread's kind of model work: a conversation unless marked (`as_kind`)."""
    return getattr(_local, "kind", "conversation")


@contextmanager
def as_kind(kind: str):
    """Marks the model calls made inside the block as this kind (ValueError for one that isn't in KINDS)."""
    if kind not in KINDS:
        raise ValueError(f"{kind} isn't a kind of model work.")
    before = current_kind()
    _local.kind = kind
    try:
        yield
    finally:
        _local.kind = before


@contextmanager
def slot(kind: Optional[str] = None):
    """Holds the one model slot for the block: waits until no one holds it and no stronger (or earlier, of the same
    kind) call is waiting. A thread already holding it passes straight through."""
    global _holder, _held_kind
    me = threading.get_ident()
    if _holder == me:
        yield
        return
    ticket = (KINDS.index(kind or current_kind()), next(_tickets))
    with _cond:
        _waiting.append(ticket)
        while _holder is not None or min(_waiting) != ticket:
            _cond.wait()
        _waiting.remove(ticket)
        _holder, _held_kind = me, KINDS[ticket[0]]
    try:
        yield
    finally:
        with _cond:
            _holder, _held_kind = None, ""
            _cond.notify_all()


def status() -> dict:
    """What holds the slot now and what's waiting, by kind (for the runtime's health)."""
    with _cond:
        return {"running": _held_kind, "waiting": [KINDS[rank] for rank, _ in sorted(_waiting)]}
