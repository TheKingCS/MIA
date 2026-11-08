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

**One line for a store** (`on_change()`, 2026-11-07, DEC-0108): a store
method decorated with `@life_events.on_change("event_added", "an event",
"calendar_event")` records an entry after every call that succeeds, named
from what it returned (its name, title or label) and referenced by its id,
so a store joins her history without hand-written calls in each method.

Appended with a plain file append (one JSON line, under a lock), never
rewritten, so "undo that" (core/undo_log.py) leaves the history intact
and adds an `undone` entry instead. Status: REAL.
"""

from __future__ import annotations

import functools
import json
import sys
import threading
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field

from core.environment import REAL, normalize
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
    "first_boot_finished": "first meetings with MIA",
    "bill_paid": "bills paid",
    "income_received": "income received",
    "expense_added": "expenses logged",
    "income_added": "income logged",
    "debt_payment": "debt payments",
    "mission_completed": "missions completed",
    "skill_evidence": "skill evidence",
    "workout_logged": "workouts",
    "played": "games and sports played",
    "meal_logged": "meals logged",
    "maintenance_done": "maintenance done",
    "rent_received": "rent received",
    "property_expense": "property expenses",
    "task_done": "tasks done",
    "project_completed": "projects finished",
    "imported": "imports",
    "starter_added": "starter sets added",
    "undone": "changes undone",
    "mission_missed": "missed days (no points lost)",
    "caught_up": "people caught up with",
    "build_finished": "builds finished",
    "goods_stocked": "goods into stock",
    "eggs_collected": "eggs collected",
    "batch_planted": "batches planted",
    "harvest": "harvests",
    "questline_finished": "questlines finished",
    "explored": "new ground explored",
    "insurance_switched": "insurance switched (money saved)",
    "dungeon_cleared": "dungeon runs cleared",
    "safety_escalation": "safety alerts",
}
# Kept for audit, never shown in a feed (wins, "what happened?").
AUDIT_ONLY = frozenset({"safety_escalation"})
# Money: never shown to a child account (core/child_accounts.py).
MONEY_TYPES = frozenset({"bill_paid", "income_received", "expense_added", "income_added", "debt_payment",
                         "rent_received", "property_expense", "imported", "insurance_switched"})
# What counts as getting something done ("what did I get done?").
WINS = ("bill_paid", "debt_payment", "mission_completed", "workout_logged", "played", "maintenance_done", "task_done",
        "project_completed", "rent_received", "income_received", "meal_logged", "build_finished", "harvest",
        "questline_finished", "insurance_switched", "dungeon_cleared")

_lock = threading.Lock()
_local = threading.local()


@dataclass
class LifeEvent:
    """One thing that happened, in the history: when, what kind, a summary in words, references to the things it's
    about ("kind:id"), a payload of numbers, where it came from, whose it is, and its environment — real (actual
    life, the default), fictional (a Living Worlds campaign) or simulated (DEC-0137), so real-life views filter to real.
    """
    event_id: str
    at: str
    type: str
    summary: str
    refs: list[str] = field(default_factory=list)
    payload: dict = field(default_factory=dict)
    source: str = "manual"
    profile_id: Optional[str] = None
    # Real-vs-fictional boundary (DEC-0137): "real" (actual life), "fictional" (a Living Worlds campaign) or
    # "simulated" (a what-if). Real-life views and the real XP ledger keep to environment == "real".
    environment: str = REAL

    @staticmethod
    def from_dict(data: dict) -> "LifeEvent":
        """An event from one saved line; missing fields take their defaults."""
        return LifeEvent(
            event_id=str(data.get("event_id", "")), at=str(data.get("at", "")), type=str(data.get("type", "")),
            summary=str(data.get("summary", "")), refs=list(data.get("refs") or []),
            payload=dict(data.get("payload") or {}), source=str(data.get("source", "manual")),
            profile_id=data.get("profile_id"), environment=normalize(data.get("environment")),
        )

    @property
    def day(self) -> str:
        """The day it happened (YYYY-MM-DD)."""
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
    """Whose event this is: the person set for this thread (crediting), else the person the store's context acts for,
    else None.
    """
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
           profile_id: Optional[str] = None, source: Optional[str] = None, environment: str = REAL) -> Optional[LifeEvent]:
    """Called by a store right after a meaningful change. Never raises:
    a history that can't be written must not undo the change itself. `environment` tags the event real (default),
    fictional or simulated (DEC-0137) so a fictional campaign's events never read as real life."""
    if where is None or getattr(_local, "quiet", 0):
        return None
    event = LifeEvent(
        event_id=uuid.uuid4().hex[:12], at=datetime.now().isoformat(timespec="seconds"), type=type,
        summary=summary, refs=[r for r in refs if r], payload=dict(payload or {}),
        source=source or getattr(_local, "source", None) or "manual", profile_id=profile_id or _who(where),
        environment=normalize(environment),
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
    from core import live, undo_log

    undo_log.note_event(event.event_id)
    live.bump()
    return event


_VERBS = (("_added", "Added"), ("_created", "Added"), ("_updated", "Changed"), ("_removed", "Removed"),
          ("_deleted", "Removed"), ("_finished", "Finished"), ("_done", "Done:"), ("_logged", "Logged"),
          ("_filed", "Filed"), ("_started", "Started"))


def _about(result, args) -> tuple[str, str]:
    """Pure logic. What a store method changed: its id and its name, from what it returned (a record, a dict) or,
    when it returned nothing, the id it was given."""
    def pick(thing, names):
        for n in names:
            value = thing.get(n) if isinstance(thing, dict) else getattr(thing, n, None)
            if isinstance(value, (str, int)) and str(value).strip():
                return str(value).strip()
        return ""

    if result is not None and not isinstance(result, (bool, str, int, float, list, tuple)):
        attrs = result if isinstance(result, dict) else vars(result) if hasattr(result, "__dict__") else {}
        ids = ["id"] + [k for k in attrs if k.endswith("_id")]
        return pick(result, ids), pick(result, ("name", "title", "label", "what", "text"))[:80]
    given = next((a for a in args if isinstance(a, str)), "")
    return given, ""


def on_change(type: str, noun: str, ref: str = "", named: bool = True):
    """Decorates a store method so each call that succeeds records a life event of `type` ("event_added"): "Added
    an event: Dentist", with a `ref:id` reference when `ref` is given. `named=False` leaves the name out of the
    line, for what's personal (a memory's words). Recording never gets in the way: the method's result is returned
    whatever happens, and a method that raises records nothing. A method that answers False changed nothing (a
    regular check that found nothing to do: textbooks' finish_reading, every 30 seconds, had recorded "Finished a
    book" each time, 2026-11-08), so it records nothing either."""
    verb = next((v for suffix, v in _VERBS if type.endswith(suffix)), "Changed")

    def wrap(method):
        @functools.wraps(method)
        def inner(self, *args, **kwargs):
            result = method(self, *args, **kwargs)
            if result is False:  # "nothing changed": nothing happened worth a line in the history
                return result
            try:
                rid, name = _about(result, args)
                summary = f"{verb} {noun}" + (f": {name}" if named and name else "")
                record(self, type, summary, refs=[f"{ref}:{rid}"] if ref and rid else [],
                       payload={"id": rid} if rid else None)
            except Exception:
                log.exception("Couldn't note the life event '%s'.", type)
            return result
        return inner
    return wrap


# ------------------------------------------------------------------ reading


class LifeEventLog:
    """One folder's log, as a store (a household's, or a person's own).
    Reads the file on each query: it's append-only and small."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """The history beside the stores (life_events.jsonl in the person's or household's folder): append-only, one
        event a line, never rewritten.
        """
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR

    @property
    def path(self) -> Path:
        """The history file."""
        return self.data_dir / FILE_NAME

    def all_events(self) -> list[LifeEvent]:
        """Every event in the file, in order; a damaged line is skipped (logged), never the whole history."""
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
        """Records an event in this log (see the module's record())."""
        return record(self, type, summary, refs, payload, **kwargs)


class PersonalLifeEventLog(LifeEventLog):
    """The person's own log (their workouts, a private budget's
    payments); a separate type so core/personal_data.py keeps it apart
    from the household's."""


def reversed_ids(events: Iterable["LifeEvent"]) -> set[str]:
    """Pure logic. The events an "undone" event took back. They stay in the
    history (nothing is rewritten), but they're no longer wins."""
    return {i for e in events if e.type == "undone" for i in (e.payload.get("reverses") or [])}


def events_for(context, since: Optional[str] = None, until: Optional[str] = None,
               types: Optional[Iterable[str]] = None, ref: Optional[str] = None,
               environment: Optional[str] = REAL) -> list[LifeEvent]:
    """The person's history: their household's log plus their own,
    newest first. A household event someone else made stays in (it's
    the household's), a personal one is only ever in its owner's log.
    `since`/`until` are ISO dates (inclusive). `environment` keeps the real-life history to real events by default
    (DEC-0137), so a Living Worlds campaign's events never surface on the real dashboard; pass None for every domain."""
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
            if environment is not None and event.environment != environment:
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
    """How many events of each kind."""
    totals: dict[str, int] = {}
    for event in events:
        totals[event.type] = totals.get(event.type, 0) + 1
    return totals


def describe(events: list[LifeEvent], period: str = "week", limit: int = 10) -> str:
    """Pure logic. What MIA says for "what did I get done this week?"."""
    label = {"today": "today", "week": "in the last 7 days", "month": "in the last 30 days",
             "year": "in the last year"}.get(period, "lately")
    events = [e for e in events if e.type not in AUDIT_ONLY]
    if not events:
        return f"Nothing recorded {label} yet."
    wins = [e for e in events if e.type in WINS]
    totals = counts(wins)
    parts = [f"{n} {TYPES.get(t, t)}" for t, n in sorted(totals.items(), key=lambda kv: -kv[1])]
    head = f"Done {label}: " + ", ".join(parts) + "." if parts else f"Nothing finished {label}, but some changes."
    latest = "; ".join(e.summary for e in events[:limit])
    return f"{head} Most recent: {latest}."
