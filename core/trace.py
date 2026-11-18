"""
core.trace
============

One id for everything that happened because of one thing (LS-01, DEC-0280; `docs/mia_os/MIA_COGNITIVE_ARCHITECTURE.md`
§2). A **trace id** is made where something starts:
- a conversation turn (`core/assistant_turn.run_assistant_turn`);
- a scheduled job (`core/scheduler.py`);
- a proposal made outside either, such as a button on a screen (`core/actions.py`).

It's carried on this thread while that work runs. Everything recorded meanwhile carries it:
- the turn's trace (`core/turn_trace.py`);
- each proposal, and its execution when it's approved later, even on another thread;
- each life event;
- each change kept for undo and in the lasting history;
- each run;
- each security log entry.

So "why did you do that?" and "what came of it?" are one lookup by id.

**Privacy.** The id is only a random label. A private turn is never traced (`turn_trace.record` skips it), so its id
appears in no turn trace, and the records that carry it say nothing about what was said. Nothing here is written
anywhere by itself.
"""

from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from typing import Iterator, Optional

_local = threading.local()


def new_id() -> str:
    """A fresh trace id: twelve hex characters."""
    return uuid.uuid4().hex[:12]


def current() -> str:
    """The trace id this thread is working under, or "" when nothing started one."""
    return getattr(_local, "trace", "") or ""


@contextmanager
def tracing(trace_id: Optional[str] = None) -> Iterator[str]:
    """Runs the block under a trace id: the one given (approving a proposal later carries its own), the one already
    running (a step inside a turn keeps the turn's), or a new one. Puts back what was there after."""
    previous = current()
    _local.trace = trace_id or previous or new_id()
    try:
        yield _local.trace
    finally:
        _local.trace = previous
