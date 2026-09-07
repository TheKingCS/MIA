"""
core.maintenance_manager
===========================

Backs the Maintenance module (modules/maintenance/module.py) — recurring
upkeep tracking for anything the user owns that needs it: vehicles,
power equipment (mower, e-bike), appliances, the property itself, and
tools. Same persisted-JSON pattern as core.journal_manager.JournalManager/
core.calendar_manager.CalendarManager: data/maintenance.json, dataclasses
with to_dict/from_dict, a manager class wrapping load/save.

No recurrence engine exists anywhere else in this app to reuse —
core.calendar_manager.CalendarEvent is a one-shot dated event with no
repeat field at all (a real, already-documented open gap, see
docs/KNOWN_ISSUES.md), and core.task_manager.Task (Project Manager's
to-do items) has a single due_date with no repeat concept either. The
closest real precedent is core.alarm_manager.Alarm's "does this recur,
is it due" shape (days: list[int] + last_triggered + a check_due(now)
pure function) — the interval/is_overdue functions below mirror that
same "take the current date as an explicit parameter, not
datetime.now() internally" testability convention, not a new one
invented for this file.

Deliberately day-interval-only, not mileage/engine-hours-based — a
vehicle's real odometer isn't a data source this app has access to.
"Every 90 days" as a stand-in for "every ~3,000 miles" is an honest v1
scope, not a fabricated mileage tracker.

Calendar integration is one-directional: schedule_task() creates a real
core.calendar_manager.CalendarEvent via self.context.calendar.add_event()
and stores its event_id on the task. Editing/deleting that event later
directly in the Calendar tool won't reflect back onto the task
(calendar_event_id can go stale) — a real, small, stated limitation,
not silently glossed over. This manager never blocks scheduling on a
conflict; the caller (modules/maintenance/module.py's Schedule dialog)
checks self.context.calendar.events_for_date() first and shows a real
warning, same "inform, don't prevent" stance every other action in this
app takes.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_MAINTENANCE_FILE = _DATA_DIR / "maintenance.json"

ASSET_CATEGORIES = ["Vehicle", "Power Equipment", "Appliance", "Property", "Tool", "Other"]


@dataclass
class MaintenanceAsset:
    asset_id: str
    name: str  # "2019 Ford F-150", "Lawn Mower", "Trek E-Bike"
    category: str = "Other"
    notes: str = ""
    created_at: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "category": self.category,
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "MaintenanceAsset":
        return MaintenanceAsset(
            asset_id=data.get("asset_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            category=data.get("category", "Other"),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
        )


@dataclass
class MaintenanceTask:
    task_id: str
    asset_id: str
    title: str  # "Oil change", "Mow lawn", "Replace HVAC filter"
    interval_days: Optional[int] = None  # None = one-time, not recurring
    last_completed: Optional[str] = None  # ISO date, None if never done
    calendar_event_id: Optional[str] = None  # set once schedule_task() places a real Calendar event
    notes: str = ""
    created_at: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "asset_id": self.asset_id,
            "title": self.title,
            "interval_days": self.interval_days,
            "last_completed": self.last_completed,
            "calendar_event_id": self.calendar_event_id,
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "MaintenanceTask":
        return MaintenanceTask(
            task_id=data.get("task_id", uuid.uuid4().hex[:10]),
            asset_id=data.get("asset_id", ""),
            title=data.get("title", ""),
            interval_days=data.get("interval_days"),
            last_completed=data.get("last_completed"),
            calendar_event_id=data.get("calendar_event_id"),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
        )


# ----------------------------------------------------------------------
# Pure recurrence logic — no Qt, no datetime.now()/date.today() called
# internally, so every case (on-time/due-soon/overdue/one-time/never-
# completed) is testable with a fixed date, same convention
# core.alarm_manager.Alarm.check_due(now) and core.daily_occasions'
# should_run_once_daily()/should_send_checkin() already established.
# ----------------------------------------------------------------------

def next_due_date(task: MaintenanceTask) -> Optional[date]:
    """None if interval_days is None (one-time task) or the task has
    never been completed yet — there's no real anchor date to compute
    forward from in either case, so this honestly returns None rather
    than guessing from created_at."""
    if task.interval_days is None or not task.last_completed:
        return None
    last = date.fromisoformat(task.last_completed)
    return date.fromordinal(last.toordinal() + task.interval_days)


def days_until_due(task: MaintenanceTask, today: date) -> Optional[int]:
    """Negative = overdue by that many days. None if next_due_date() is None."""
    due = next_due_date(task)
    if due is None:
        return None
    return (due - today).days


def is_overdue(task: MaintenanceTask, today: date) -> bool:
    remaining = days_until_due(task, today)
    return remaining is not None and remaining < 0


class MaintenanceManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._assets: list[MaintenanceAsset] = []
        self._tasks: list[MaintenanceTask] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _MAINTENANCE_FILE.exists():
            self._assets, self._tasks = [], []
            return
        try:
            raw = json.loads(_MAINTENANCE_FILE.read_text(encoding="utf-8"))
            self._assets = [MaintenanceAsset.from_dict(d) for d in raw.get("assets", [])]
            self._tasks = [MaintenanceTask.from_dict(d) for d in raw.get("tasks", [])]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load maintenance.json — starting with an empty list.")
            self._assets, self._tasks = [], []

    def reload(self) -> None:
        self._load()

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _MAINTENANCE_FILE.write_text(
            json.dumps(
                {
                    "assets": [a.to_dict() for a in self._assets],
                    "tasks": [t.to_dict() for t in self._tasks],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Assets
    # ------------------------------------------------------------------

    def add_asset(self, name: str, category: str = "Other", notes: str = "") -> MaintenanceAsset:
        asset = MaintenanceAsset(
            asset_id=uuid.uuid4().hex[:10],
            name=name,
            category=category,
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._assets.append(asset)
        self._save()
        log.info("Maintenance asset added: '%s' (%s)", name, category)
        return asset

    def update_asset(self, asset_id: str, **fields) -> MaintenanceAsset:
        asset = self.get_asset(asset_id)
        if asset is None:
            raise ValueError(f"No maintenance asset with id '{asset_id}'.")
        for key, value in fields.items():
            if not hasattr(asset, key):
                raise ValueError(f"MaintenanceAsset has no field '{key}'.")
            setattr(asset, key, value)
        self._save()
        return asset

    def delete_asset(self, asset_id: str) -> None:
        """Also deletes every task for this asset — an asset going away
        shouldn't leave orphaned tasks pointing at nothing."""
        self._assets = [a for a in self._assets if a.asset_id != asset_id]
        self._tasks = [t for t in self._tasks if t.asset_id != asset_id]
        self._save()

    def get_asset(self, asset_id: str) -> Optional[MaintenanceAsset]:
        for asset in self._assets:
            if asset.asset_id == asset_id:
                return asset
        return None

    def all_assets(self) -> list[MaintenanceAsset]:
        return sorted(self._assets, key=lambda a: a.name.lower())

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def add_task(
        self,
        asset_id: str,
        title: str,
        interval_days: Optional[int] = None,
        last_completed: Optional[str] = None,
        notes: str = "",
    ) -> MaintenanceTask:
        task = MaintenanceTask(
            task_id=uuid.uuid4().hex[:10],
            asset_id=asset_id,
            title=title,
            interval_days=interval_days,
            last_completed=last_completed,
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._tasks.append(task)
        self._save()
        log.info("Maintenance task added: '%s' for asset %s", title, asset_id)
        return task

    def update_task(self, task_id: str, **fields) -> MaintenanceTask:
        task = self.get_task(task_id)
        if task is None:
            raise ValueError(f"No maintenance task with id '{task_id}'.")
        for key, value in fields.items():
            if not hasattr(task, key):
                raise ValueError(f"MaintenanceTask has no field '{key}'.")
            setattr(task, key, value)
        self._save()
        return task

    def delete_task(self, task_id: str) -> None:
        self._tasks = [t for t in self._tasks if t.task_id != task_id]
        self._save()

    def get_task(self, task_id: str) -> Optional[MaintenanceTask]:
        for task in self._tasks:
            if task.task_id == task_id:
                return task
        return None

    def all_tasks(self) -> list[MaintenanceTask]:
        return list(self._tasks)

    def tasks_for_asset(self, asset_id: str) -> list[MaintenanceTask]:
        return [t for t in self._tasks if t.asset_id == asset_id]

    def mark_complete(self, task_id: str, completed_date: Optional[str] = None) -> MaintenanceTask:
        task = self.get_task(task_id)
        if task is None:
            raise ValueError(f"No maintenance task with id '{task_id}'.")
        task.last_completed = completed_date or date.today().isoformat()
        self._save()
        log.info("Maintenance task completed: '%s' on %s", task.title, task.last_completed)
        return task

    # ------------------------------------------------------------------
    # Calendar integration
    # ------------------------------------------------------------------

    def schedule_task(self, task_id: str, date_str: str):
        """Creates a real core.calendar_manager.CalendarEvent for this
        task via self.context.calendar and stores its event_id on the
        task. Does NOT check for conflicts itself — the caller (the
        Schedule dialog) reads self.context.calendar.events_for_date()
        first and shows the user a real warning, same "inform, don't
        block" stance the rest of this app takes on user actions."""
        task = self.get_task(task_id)
        if task is None:
            raise ValueError(f"No maintenance task with id '{task_id}'.")
        asset = self.get_asset(task.asset_id)
        asset_name = asset.name if asset is not None else "Unknown asset"
        event = self.context.calendar.add_event(
            title=f"Maintenance: {task.title} ({asset_name})",
            date=date_str,
            notes=task.notes,
        )
        task.calendar_event_id = event.event_id
        self._save()
        log.info("Scheduled maintenance task '%s' on %s (calendar event %s)", task.title, date_str, event.event_id)
        return event
