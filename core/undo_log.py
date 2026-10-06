"""
core.undo_log
===============

"Undo that" (2026-10-01, accounts stage 5): when MIA changes something
for you (adds an expense, checks off a chore, logs a reading) and got it
wrong, you can take it back.

How: while an Assistant tool that changes things runs
(core/assistant_actions.py), every data file it writes through
`atomic_write_text` (core/atomic_write.py, which nearly every store uses)
has its previous contents kept, once per file. Undo writes those back
and reloads the stores that read them, then the screens refresh. It
works for every tool without each one writing its own undo.

Kept in memory only, the last `KEEP` changes per person: undo is for
"oops, just now", not history. A change made on someone's phone is
theirs to undo. Undo can't reach outside MIA's files: a sent email (only
ever by pressing Send) stays sent.
"""

from __future__ import annotations

import threading
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

KEEP = 20
_local = threading.local()


@dataclass
class Change:
    label: str  # what MIA did, e.g. "add_expense"
    profile_id: Optional[str]
    at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    files: dict = field(default_factory=dict)  # Path -> previous bytes, or None if it didn't exist
    events: list = field(default_factory=list)  # life events recorded during it (their ids)


@contextmanager
def recording(label: str, profile_id: Optional[str]):
    """Keep what each file looked like before this change (this thread only)."""
    change = Change(label, profile_id)
    previous = getattr(_local, "change", None)
    _local.change = change
    try:
        yield change
    finally:
        _local.change = previous


def note_event(event_id: str) -> None:
    """Called by core/life_events.record: this event belongs to the change
    being recorded, so undoing it can mark the event reversed."""
    change = getattr(_local, "change", None)
    if change is not None:
        change.events.append(event_id)


def before_write(path: Path) -> None:
    """Called by atomic_write_text before it replaces a file."""
    change = getattr(_local, "change", None)
    if change is None:
        return
    path = Path(path)
    if path not in change.files:
        try:
            change.files[path] = path.read_bytes() if path.exists() else None
        except OSError:
            change.files[path] = None


class UndoLog:
    def __init__(self) -> None:
        self._changes: dict[Optional[str], deque] = {}
        self._lock = threading.Lock()

    def add(self, change: Change) -> None:
        if not change.files:
            return
        with self._lock:
            self._changes.setdefault(change.profile_id, deque(maxlen=KEEP)).append(change)

    def recent(self, profile_id: Optional[str]) -> list[Change]:
        with self._lock:
            return list(reversed(self._changes.get(profile_id, ())))

    def pop(self, profile_id: Optional[str]) -> Optional[Change]:
        with self._lock:
            changes = self._changes.get(profile_id)
            return changes.pop() if changes else None


def _restore(change: Change) -> list[Path]:
    for path, old in change.files.items():
        if old is None:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(f".{path.name}.undo")
            tmp.write_bytes(old)
            tmp.replace(path)
    return list(change.files)


def _store_files(store) -> set[Path]:
    try:
        return {v for v in vars(store).values() if isinstance(v, Path)}
    except TypeError:
        return set()


def reload_stores(context, paths: list[Path]) -> int:
    """Stores that read any of `paths` read them again. Returns how many."""
    wanted = {Path(p) for p in paths}
    personal = getattr(context, "personal_data", None)
    registered = personal.registered_store_types() if personal is not None else set()
    seen: dict[int, object] = {}
    candidates = list(vars(context).values())
    # A person's view (core/personal_data.ScopedView, the phone and the web)
    # keeps its own stores aside and reads the rest, the config among them,
    # from the main context underneath.
    base = vars(context).get("_base")
    if base is not None:
        candidates += list(vars(context).get("_stores", {}).values()) + list(vars(base).values())
    for store in candidates + (personal.all_known_stores() if personal is not None else []):
        if store is not None and id(store) not in seen and _store_files(store) & wanted:
            seen[id(store)] = store
    reloaded = 0
    for store in seen.values():
        if type(store) in registered and personal is not None:
            fresh = type(store)(store.context, data_dir=store.data_dir)
            personal.replace_store(store, fresh)
            reloaded += 1
        elif callable(getattr(store, "_load", None)):
            store._load()
            reloaded += 1
        else:
            log.warning("Undo restored a file %s doesn't reload by itself; a restart shows it.", type(store).__name__)
    return reloaded


def undo_last(context, profile_id: Optional[str]) -> Optional[Change]:
    """Put the person's most recent change back. None if there's nothing."""
    undo = getattr(context, "undo", None)
    change = undo.pop(profile_id) if undo is not None else None
    if change is None:
        return None
    reload_stores(context, _restore(change))
    from core import live

    live.bump()
    # History stays: the undo is one more thing that happened (core/life_events.py).
    from core import life_events

    life_events.record(getattr(context, "life_events", None), "undone", f"Undid: {change.label.replace('_', ' ')}",
                       [], {"label": change.label, "reverses": list(change.events)}, profile_id=profile_id)
    from core.main_thread import publish

    publish(context, "records.changed", action="undo")
    log.info("Undid '%s' for %s (%d file(s)).", change.label, profile_id, len(change.files))
    return change
