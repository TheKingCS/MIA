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

Kept in memory, the last `KEEP` changes per person: undo is for "oops,
just now". Every change is also kept on disk for 30 days by the lasting
history (core/change_history.py, UI-3), which `add` writes to, `forget`
answers (changes it already put back leave memory) and `undo_last` marks. A change made on someone's phone is
theirs to undo. Undo can't reach outside MIA's files: a sent email (only
ever by pressing Send) stays sent. A log of what happened written during a
change (the Fix-It Log's stumbles) is written inside `outside_undo()`, so
undo never takes it back.

Two settings are never put back by an undo of another change (`STICKY_KEYS`): a
stop-everything in force and the standing yeses. They live in the config file
beside ordinary settings, so when an undo restores that file, `keep_sticky`
carries today's values of those two into the restored copy: undoing a theme
change can't lift a stop or bring back a yes he took back.
"""

from __future__ import annotations

import json
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
# Never put back by an undo of another change: the stop (core/stop.py) and the standing yeses (core/kind_grants.py).
STICKY_KEYS = ("mia.stop_everything", "grants.kinds")
_ABSENT = object()


@dataclass
class Change:
    """One undoable change: what MIA did, whose it was, when, each file's bytes before it (None for a file it made),
    the life events it recorded, who made it (the person, or MIA herself), its description for the lasting history
    (the approved sentence, or a tool's name and arguments) and its id there.
    """
    label: str  # what MIA did, e.g. "add_expense"
    profile_id: Optional[str]
    at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    files: dict = field(default_factory=dict)  # Path -> previous bytes, or None if it didn't exist
    events: list = field(default_factory=list)  # life events recorded during it (their ids)
    by: str = "person"  # "mia" when she made it: undoing it corrects her (core/corrections.py)
    summary: str = ""  # the sentence that was approved, for an action (the lasting history shows it)
    change_id: str = field(default_factory=lambda: __import__("uuid").uuid4().hex[:12])


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


@contextmanager
def outside_undo():
    """Writes inside this block are never part of the change being recorded: a log of what happened (the Fix-It
    Log's stumbles), which "undo that" must never take back, nor count as a change when nothing else changed."""
    previous = getattr(_local, "change", None)
    _local.change = None
    try:
        yield
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
    """The undoable changes, the last KEEP (20) per person, newest last; kept in memory and safe across threads."""
    def __init__(self) -> None:
        """Starts with no changes."""
        self._changes: dict[Optional[str], deque] = {}
        self._lock = threading.Lock()

    def add(self, change: Change) -> None:
        """Keeps a change for its person (one that touched no file is dropped), and in the person's lasting history
        on disk (core/change_history.py, UI-3), where "undo what you did this afternoon" finds it after a restart."""
        if not change.files:
            return
        with self._lock:
            self._changes.setdefault(change.profile_id, deque(maxlen=KEEP)).append(change)
        from core import change_history

        change_history.keep(change)

    def forget(self, change_ids: set) -> None:
        """Drops changes the lasting history has already put back, so "undo that" can't restore them a second time."""
        with self._lock:
            for profile_id, changes in self._changes.items():
                self._changes[profile_id] = deque((c for c in changes if c.change_id not in change_ids), maxlen=KEEP)

    def recent(self, profile_id: Optional[str]) -> list[Change]:
        """A person's changes, newest first."""
        with self._lock:
            return list(reversed(self._changes.get(profile_id, ())))

    def pop(self, profile_id: Optional[str]) -> Optional[Change]:
        """Takes a person's newest change off the log, or None."""
        with self._lock:
            changes = self._changes.get(profile_id)
            return changes.pop() if changes else None


def _dig(data: dict, dotted: str):
    """Pure logic. The value at a dotted path in a nested dict, or `_ABSENT`."""
    for part in dotted.split("."):
        if not isinstance(data, dict) or part not in data:
            return _ABSENT
        data = data[part]
    return data


def _put(data: dict, dotted: str, value) -> None:
    """Pure logic. Sets (or, for `_ABSENT`, removes) the value at a dotted path in a nested dict."""
    parts = dotted.split(".")
    for part in parts[:-1]:
        inner = data.get(part)
        if not isinstance(inner, dict):
            if value is _ABSENT:
                return
            inner = data[part] = {}
        data = inner
    if value is _ABSENT:
        data.pop(parts[-1], None)
    else:
        data[parts[-1]] = value


def _carry_sticky(now: dict, old: dict) -> dict:
    """Pure logic. `old` (a config about to be restored) with today's `STICKY_KEYS` from `now`: the device's own,
    and each person's in their record's settings. A person who exists only in `old` keeps none: no stop, no yes."""
    for key in STICKY_KEYS:
        _put(old, key, _dig(now, key))
    for profile_id, record in (old.get("profiles") or {}).items():
        if not isinstance(record, dict):
            continue
        current = ((now.get("profiles") or {}).get(profile_id) or {}).get("settings") or {}
        settings = dict(record.get("settings") or {})
        for key in STICKY_KEYS:
            if key in current:
                settings[key] = current[key]
            else:
                settings.pop(key, None)
        if settings or "settings" in record:
            record["settings"] = settings
    return old


def keep_sticky(path: Path, old: Optional[bytes]) -> Optional[bytes]:
    """What to write when an undo puts `path` back: `old`, except that the config file keeps today's stop and
    standing yeses (`STICKY_KEYS`). If the config can't be read as it is now, the file is left as it is (returned
    unchanged from disk) rather than restored without them: a stop is never lifted by a failure."""
    from core.config_manager import _CONFIG_FILE

    if Path(path) != _CONFIG_FILE or not Path(path).exists():
        return old
    current_bytes = Path(path).read_bytes()
    try:
        now = json.loads(current_bytes.decode("utf-8"))
        restored = json.loads(old.decode("utf-8")) if old is not None else {}
        if not isinstance(now, dict) or not isinstance(restored, dict):
            raise ValueError("the config isn't a JSON object")
    except (ValueError, UnicodeDecodeError):
        log.exception("Undo left the config as it is: it couldn't carry the stop and the standing yeses over")
        return current_bytes
    return json.dumps(_carry_sticky(now, restored), indent=4).encode("utf-8")


def _restore(change: Change) -> list[Path]:
    """Puts each file back as it was before a change (a file the change made is deleted), through a temporary file
    so a restore is never half-written; returns the files touched. The config file keeps today's stop and standing
    yeses (`keep_sticky`).
    """
    for path, old in change.files.items():
        old = keep_sticky(path, old)
        if old is None:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(f".{path.name}.undo")
            tmp.write_bytes(old)
            tmp.replace(path)
    return list(change.files)


def _store_files(store) -> set[Path]:
    """The file paths a store holds as attributes, which is how undo finds the stores to reload after restoring their files."""
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
    """Put the person's most recent change back, and mark it undone in the lasting history so it's never put back
    twice. None if there's nothing."""
    undo = getattr(context, "undo", None)
    change = undo.pop(profile_id) if undo is not None else None
    if change is None:
        return None
    reload_stores(context, _restore(change))
    from core import change_history

    change_history.mark_undone(profile_id, change.change_id)  # the lasting history never puts it back a second time
    from core import live

    live.bump()
    # History stays: the undo is one more thing that happened (core/life_events.py).
    from core import life_events

    life_events.record(getattr(context, "life_events", None), "undone", f"Undid: {change.label.replace('_', ' ')}",
                       [], {"label": change.label, "reverses": list(change.events)}, profile_id=profile_id)
    from core.main_thread import publish

    publish(context, "records.changed", action="undo")
    if change.by == "mia":
        from core import corrections

        corrections.undone(context, change.label)
    log.info("Undid '%s' for %s (%d file(s)).", change.label, profile_id, len(change.files))
    return change
