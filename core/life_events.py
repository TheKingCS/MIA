"""
core.life_events
==================

Life events (2026-10-05, Engine Phase 1, docs/ENGINE_PHASE1_PLAN.md):
an append-only history of the meaningful things that happen in a
person's life: a bill paid, a mission completed (and the skill evidence
it earned), a workout or meal logged, maintenance done, rent received,
an import, a starter set added, an undo.

**What happened, not what's true now.** The stores stay the source of
truth for the current state (the bill, its last-paid date). This log is
the history beside them, so MIA can answer "what changed?", "what did I
get done this month?" and feed recent wins into Life State
(core/context_assembler.py). It isn't core/activity_log_manager.py: that
one logs app usage (screens opened, notifications) for the device.

**Where entries go.** Each store records into `life_events.jsonl` in
its own folder (`store.data_dir`), so history follows the data: a
household's bills into that household's folder, a private budget into
the person's private folder, workouts into the person's own folder.
Device-level stores (Missions) use `data/`. Readers combine the
household's log and the person's own (`events_for()`).

**Each entry:** `event_id`, `at` (ISO time), `type`, `summary` (one
plain line, made in code), `refs` (`kind:id` strings, the same ids the
stores use), `payload` (numbers and dates), `source` and `profile_id`
(who). Sources: `manual` (the person, in the app; the default),
`assistant` (MIA, asked by the person), `phone`, `import`, `inferred`
(MIA did it on her own, e.g. auto-tagging).

Appended with a plain file append (one JSON line, under a lock), never
rewritten, so "undo that" (core/undo_log.py) leaves the history intact
and adds an `undone` entry instead. Status: REAL.
"""

from __future__ import annotations

import json
import sys
import threading
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "life_events.jsonl"
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SOURCES = ("manual", "assistant", "phone", "import", "inferred")

# Every type MIA records, with the plain word used when counting them.
TYPES = {
    "bill_paid": "bills paid",
    "income_received": "income received",
    "expense_added": "expenses logged",
    "income_added": "income logged",
    "debt_payment": "debt payments",
    "mission_completed": "missions completed",
    "skill_evidence": "skill evidence",
    "workout_logged": "workouts",
    "meal_logged": "meals logged",
    "maintenance_done": "maintenance done",
    "rent_received": "rent received",
    "property_expense": "property expenses",
    "task_done": "tasks done",
    "project_completed": "projects finished",
    "imported": "imports",
    "starter_added": "starter sets added",
    "undone": "changes undone",
}
# Money: never shown to a child account (core/child_accounts.py).
MONEY_TYPES = frozenset({"bill_paid", "income_received", "expense_added", "income_added", "debt_payment",
                         "rent_received", "property_expense", "imported"})
# What counts as getting something done ("what did I get done?").
WINS = ("bill_paid", "debt_payment", "mission_completed", "workout_logged", "maintenance_done", "task_done",
        "project_completed", "rent_received", "income_received", "meal_logged")

_lock = threading.Lock()
_local = threading.local()


@dataclass
class LifeEvent:
    event_id: str
    at: str
    type: str
    summary: str
    refs: list[str] = field(default_factory=list)
    payload: dict = field(default_factory=dict)
    source: str = "manual"
    profile_id: Optional[str] = None

    @staticmethod
    def from_dict(data: dict) -> "LifeEvent":
        return LifeEvent(
            event_id=str(data.get("event_id", "")), at=str(data.get("at", "")), type=str(data.get("type", "")),
            summary=str(data.get("summary", "")), refs=list(data.get("refs") or []),
            payload=dict(data.get("payload") or {}), source=str(data.get("source", "manual")),
            profile_id=data.get("profile_id"),
        )

    @property
    def day(self) -> str:
        return self.at[:10]


# ------------------------------------------------------------------ who and how


@contextmanager
def acting(source: str, profile_id: Optional[str] = None):
    """Everything recorded on this thread inside comes from `source` (and
    `profile_id`, when given): the Assistant, the phone, an import."""
    previous = (getattr(_local, "source", None), getattr(_local, "profile_id", None))
    _local.source, _local.profile_id = source, profile_id or previous[1]
    try:
        yield
    finally:
        _local.source, _local.profile_id = previous


@contextmanager
def quiet():
    """Inside, nested records are skipped: marking a bill paid records
    `bill_paid`, not also the `expense_added` it makes on the way."""
    depth = getattr(_local, "quiet", 0)
    _local.quiet = depth + 1
    try:
        yield
    finally:
        _local.quiet = depth


def _who(where) -> Optional[str]:
    explicit = getattr(_local, "profile_id", None)
    if explicit:
        return explicit
    context = getattr(where, "context", None)
    if context is None:
        return None
    from core.person_settings import person_id

    try:
        return person_id(context)
    except Exception:
        return None


def folder_of(where) -> Path:
    """The folder a store (or a log) keeps its data in. A device-level
    store without a `data_dir` (Missions) uses its own module's data
    folder, so tests that point that store elsewhere point this too."""
    data_dir = getattr(where, "data_dir", None)
    if data_dir is not None:
        return Path(data_dir)
    module = sys.modules.get(type(where).__module__)
    module_dir = getattr(module, "_DATA_DIR", None)
    return Path(module_dir) if module_dir is not None else _DATA_DIR


def record(where, type: str, summary: str, refs: Iterable[str] = (), payload: Optional[dict] = None,
           profile_id: Optional[str] = None, source: Optional[str] = None) -> Optional[LifeEvent]:
    """Called by a store right after a meaningful change. Never raises:
    a history that can't be written must not undo the change itself."""
    if where is None or getattr(_local, "quiet", 0):
        return None
    event = LifeEvent(
        event_id=uuid.uuid4().hex[:12], at=datetime.now().isoformat(timespec="seconds"), type=type,
        summary=summary, refs=[r for r in refs if r], payload=dict(payload or {}),
        source=source or getattr(_local, "source", None) or "manual", profile_id=profile_id or _who(where),
    )
    try:
        folder = folder_of(where)
        folder.mkdir(parents=True, exist_ok=True)
        line = json.dumps(asdict(event), ensure_ascii=False)
        with _lock, open(folder / FILE_NAME, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        log.exception("Couldn't record the life event '%s'.", type)
        return None
    return event


# ------------------------------------------------------------------ reading


class LifeEventLog:
    """One folder's log, as a store (a household's, or a person's own).
    Reads the file on each query: it's append-only and small."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR

    @property
    def path(self) -> Path:
        return self.data_dir / FILE_NAME

    def all_events(self) -> list[LifeEvent]:
        if not self.path.exists():
            return []
        events = []
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(LifeEvent.from_dict(json.loads(line)))
                except (json.JSONDecodeError, TypeError, AttributeError):
                    log.warning("Skipped a damaged line in %s.", self.path)
        except OSError:
            log.exception("Couldn't read %s.", self.path)
        return events

    def record(self, type: str, summary: str, refs: Iterable[str] = (), payload: Optional[dict] = None,
               **kwargs) -> Optional[LifeEvent]:
        return record(self, type, summary, refs, payload, **kwargs)


class PersonalLifeEventLog(LifeEventLog):
    """The person's own log (their workouts, a private budget's
    payments); a separate type so core/personal_data.py keeps it apart
    from the household's."""


def events_for(context, since: Optional[str] = None, until: Optional[str] = None,
               types: Optional[Iterable[str]] = None, ref: Optional[str] = None) -> list[LifeEvent]:
    """The person's history: their household's log plus their own,
    newest first. A household event someone else made stays in (it's
    the household's), a personal one is only ever in its owner's log.
    `since`/`until` are ISO dates (inclusive)."""
    wanted = set(types) if types else None
    from core.child_accounts import is_child

    child = getattr(context, "config", None) is not None and is_child(context)
    seen: set[str] = set()
    found: list[tuple[str, int, LifeEvent]] = []  # (at, position) keeps same-second events in order
    logs = [getattr(context, "life_events", None), getattr(context, "personal_life_events", None)]
    # A private budget (core/personal_data.py) keeps its history in its own folder.
    budget = getattr(context, "budget", None)
    if budget is not None and not any(log_ is not None and log_.data_dir == folder_of(budget) for log_ in logs):
        logs.append(LifeEventLog(context, folder_of(budget)))
    for log_ in logs:
        if log_ is None:
            continue
        for position, event in enumerate(log_.all_events()):
            if event.event_id in seen:
                continue
            if since and event.day < since or until and event.day > until:
                continue
            if wanted is not None and event.type not in wanted or child and event.type in MONEY_TYPES:
                continue
            if ref and ref not in event.refs:
                continue
            seen.add(event.event_id)
            found.append((event.at, position, event))
    return [event for _at, _pos, event in sorted(found, key=lambda item: (item[0], item[1]), reverse=True)]


PERIODS = {"today": 0, "week": 6, "month": 29, "year": 364}


def period_start(period: str, today: Optional[date] = None) -> str:
    """Pure logic. "week" = the last 7 days including today, and so on."""
    today = today or date.today()
    return (today - timedelta(days=PERIODS.get(period, 6))).isoformat()


def counts(events: list[LifeEvent]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for event in events:
        totals[event.type] = totals.get(event.type, 0) + 1
    return totals


def describe(events: list[LifeEvent], period: str = "week", limit: int = 10) -> str:
    """Pure logic. What MIA says for "what did I get done this week?"."""
    label = {"today": "today", "week": "in the last 7 days", "month": "in the last 30 days",
             "year": "in the last year"}.get(period, "lately")
    if not events:
        return f"Nothing recorded {label} yet."
    wins = [e for e in events if e.type in WINS]
    totals = counts(wins)
    parts = [f"{n} {TYPES.get(t, t)}" for t, n in sorted(totals.items(), key=lambda kv: -kv[1])]
    head = f"Done {label}: " + ", ".join(parts) + "." if parts else f"Nothing finished {label}, but some changes."
    latest = "; ".join(e.summary for e in events[:limit])
    return f"{head} Most recent: {latest}."
