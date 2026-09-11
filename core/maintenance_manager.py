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

v2 adds six trigger types (Calendar/Runtime/Mileage/Cycles/Condition/
Sensor) plus a derived Prediction estimate. Runtime/Mileage/Cycles/
Condition share one "meter" mechanism (a cumulative reading vs. an
interval since last service); Sensor uses a "threshold" mechanism (a
reading crossing a line). Neither fabricates live telemetry — both read
from core.data_logger_manager.DataLoggerManager (self.context.data_logger),
which already exists precisely for this ("no hardware-specific reading
producer exists yet... a future real-sensor integration is just another
caller of add_reading()" — its own docstring). A task's meter/sensor
values are logged manually via log_reading() until real hardware exists
to call the same method instead.

Documents (receipts/warranties/manuals) mirror core.trip_manager.Trip's
photo pattern exactly: a bare filename list on the asset, real files
copied into project-root maintenance_documents/<asset_id>/ (a sibling of
data/, not inside it — same reason trip_photos/ sits outside data/:
core.backup_manager only walks the data/ tree).

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
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.data_logger_manager import Reading
from core.gamification import grant_xp
from core.logger import get_logger

log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"
_MAINTENANCE_FILE = _DATA_DIR / "maintenance.json"
_DOCUMENT_ROOT = _PROJECT_ROOT / "maintenance_documents"

ASSET_CATEGORIES = ["Vehicle", "Power Equipment", "Appliance", "Property", "Tool", "Other"]

# trigger_type values that use the cumulative-meter mechanism (a reading
# minus its value at last completion, compared against an interval) —
# only the label/unit differs between them.
METER_TRIGGER_TYPES = ["runtime", "mileage", "cycles", "condition"]
# trigger_type values that use the threshold mechanism (latest reading
# crossing a line, not cumulative).
THRESHOLD_TRIGGER_TYPES = ["sensor"]
TRIGGER_TYPES = ["calendar"] + METER_TRIGGER_TYPES + THRESHOLD_TRIGGER_TYPES
# Sensible default units shown when a trigger type is first selected in
# the task dialog — all freely editable, not enforced here.
DEFAULT_METER_UNITS = {
    "runtime": "engine hours",
    "mileage": "miles",
    "cycles": "starts",
    "condition": "",
}


@dataclass
class MaintenanceAsset:
    asset_id: str
    name: str  # "2019 Ford F-150", "Lawn Mower", "Trek E-Bike"
    category: str = "Other"
    notes: str = ""
    created_at: str = ""  # ISO datetime
    purchase_date: str = ""  # ISO date, optional
    serial_number: str = ""
    manufacturer: str = ""
    model: str = ""
    documents: list[str] = field(default_factory=list)  # bare filenames under maintenance_documents/<asset_id>/

    def to_dict(self) -> dict:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "category": self.category,
            "notes": self.notes,
            "created_at": self.created_at,
            "purchase_date": self.purchase_date,
            "serial_number": self.serial_number,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "documents": list(self.documents),
        }

    @staticmethod
    def from_dict(data: dict) -> "MaintenanceAsset":
        return MaintenanceAsset(
            asset_id=data.get("asset_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            category=data.get("category", "Other"),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
            purchase_date=data.get("purchase_date", ""),
            serial_number=data.get("serial_number", ""),
            manufacturer=data.get("manufacturer", ""),
            model=data.get("model", ""),
            documents=list(data.get("documents", [])),
        )


@dataclass
class MaintenanceTask:
    task_id: str
    asset_id: str
    title: str  # "Oil change", "Mow lawn", "Replace HVAC filter"
    interval_days: Optional[int] = None  # None = one-time, not recurring — calendar trigger only
    last_completed: Optional[str] = None  # ISO date, None if never done
    calendar_event_id: Optional[str] = None  # set once schedule_task() places a real Calendar event
    notes: str = ""
    created_at: str = ""  # ISO datetime
    trigger_type: str = "calendar"  # one of TRIGGER_TYPES
    # Meter mechanism (runtime/mileage/cycles/condition) — a cumulative
    # reading vs. an interval since last service. Values are logged via
    # log_reading() into a Data Logger series keyed by this task's id.
    meter_unit: str = ""
    meter_interval: Optional[float] = None
    last_completed_meter_value: Optional[float] = None
    # Threshold mechanism (sensor) — latest reading crossing a line.
    threshold_value: Optional[float] = None
    threshold_direction: str = "below"  # "below" or "above"
    # Opt-in: auto-create a Calendar event for today once due, checked
    # from the dashboard's existing refresh tick. Off by default — see
    # core/maintenance_manager.py module docstring.
    auto_schedule: bool = False

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
            "trigger_type": self.trigger_type,
            "meter_unit": self.meter_unit,
            "meter_interval": self.meter_interval,
            "last_completed_meter_value": self.last_completed_meter_value,
            "threshold_value": self.threshold_value,
            "threshold_direction": self.threshold_direction,
            "auto_schedule": self.auto_schedule,
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
            trigger_type=data.get("trigger_type", "calendar"),
            meter_unit=data.get("meter_unit", ""),
            meter_interval=data.get("meter_interval"),
            last_completed_meter_value=data.get("last_completed_meter_value"),
            threshold_value=data.get("threshold_value"),
            threshold_direction=data.get("threshold_direction", "below"),
            auto_schedule=data.get("auto_schedule", False),
        )

    @property
    def series_id(self) -> str:
        """The Data Logger series key this task's meter/sensor readings are logged under."""
        return f"maintenance_{self.task_id}"

    @property
    def is_meter_task(self) -> bool:
        return self.trigger_type in METER_TRIGGER_TYPES

    @property
    def is_sensor_task(self) -> bool:
        return self.trigger_type in THRESHOLD_TRIGGER_TYPES


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


# ----------------------------------------------------------------------
# Meter mechanism (runtime/mileage/cycles/condition) and threshold
# mechanism (sensor) — same "take readings as an explicit parameter, no
# hidden Data Logger lookup" testability convention as the calendar
# functions above.
# ----------------------------------------------------------------------

def _latest_reading_value(readings: list[Reading]) -> Optional[float]:
    if not readings:
        return None
    return sorted(readings, key=lambda r: r.timestamp)[-1].value


def meter_used_since_last(task: MaintenanceTask, readings: list[Reading]) -> Optional[float]:
    """Latest logged value minus the value at last completion. None if
    there are no readings yet, or the task has never been completed (no
    baseline to measure "used since" from)."""
    if task.last_completed_meter_value is None:
        return None
    latest = _latest_reading_value(readings)
    if latest is None:
        return None
    return latest - task.last_completed_meter_value


def is_meter_task_due(task: MaintenanceTask, readings: list[Reading]) -> bool:
    if task.meter_interval is None:
        return False
    used = meter_used_since_last(task, readings)
    if used is None:
        return False
    return used >= task.meter_interval


def is_sensor_task_due(task: MaintenanceTask, readings: list[Reading]) -> bool:
    if task.threshold_value is None:
        return False
    latest = _latest_reading_value(readings)
    if latest is None:
        return False
    if task.threshold_direction == "above":
        return latest >= task.threshold_value
    return latest <= task.threshold_value


def predicted_due_date(
    task: MaintenanceTask, readings: list[Reading], today: date
) -> Optional[tuple[date, str]]:
    """
    Linear usage-rate projection for a meter-type task: rate = (last
    value - first value) / (last timestamp - first timestamp) across all
    logged readings, projected forward from the remaining units until
    meter_interval is reached. Returns (estimated_date, caveat_string),
    e.g. (date(...), "~3 weeks at current usage (avg 2.1 hrs/week over 4
    logged readings)").

    Returns None — never a fabricated guess — when: the task isn't a
    meter task, fewer than 2 readings exist, the usage rate is <= 0 (not
    trending toward due), or the task has no completion baseline yet.
    """
    if not task.is_meter_task or task.meter_interval is None:
        return None
    if len(readings) < 2:
        return None
    used = meter_used_since_last(task, readings)
    if used is None:
        return None
    remaining = task.meter_interval - used
    if remaining <= 0:
        return None  # already due — a projection forward makes no sense

    ordered = sorted(readings, key=lambda r: r.timestamp)
    first, last = ordered[0], ordered[-1]
    first_dt = datetime.fromisoformat(first.timestamp)
    last_dt = datetime.fromisoformat(last.timestamp)
    elapsed_days = (last_dt - first_dt).total_seconds() / 86400
    if elapsed_days <= 0:
        return None
    rate_per_day = (last.value - first.value) / elapsed_days
    if rate_per_day <= 0:
        return None  # usage isn't trending upward — no honest projection to make

    days_remaining = remaining / rate_per_day
    estimated = date.fromordinal(today.toordinal() + round(days_remaining))

    rate_per_week = rate_per_day * 7
    weeks_remaining = days_remaining / 7
    unit = task.meter_unit or "units"
    if weeks_remaining >= 1.5:
        when = f"~{round(weeks_remaining)} weeks"
    else:
        when = f"~{max(1, round(days_remaining))} days"
    caveat = f"{when} at current usage (avg {rate_per_week:.1f} {unit}/week over {len(readings)} logged readings)"
    return estimated, caveat


class MaintenanceManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._assets: list[MaintenanceAsset] = []
        self._tasks: list[MaintenanceTask] = []
        self._load()
        try:
            _DOCUMENT_ROOT.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Same rationale as TripManager's photo folder: don't crash
            # the app over a missing/unmounted storage location — the
            # document methods below just log and no-op if this folder
            # isn't there when actually needed.
            log.warning("Could not create/access maintenance document folder: %s", _DOCUMENT_ROOT)

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

    def add_asset(
        self,
        name: str,
        category: str = "Other",
        notes: str = "",
        purchase_date: str = "",
        serial_number: str = "",
        manufacturer: str = "",
        model: str = "",
    ) -> MaintenanceAsset:
        asset = MaintenanceAsset(
            asset_id=uuid.uuid4().hex[:10],
            name=name,
            category=category,
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
            purchase_date=purchase_date,
            serial_number=serial_number,
            manufacturer=manufacturer,
            model=model,
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
        shouldn't leave orphaned tasks pointing at nothing — and removes
        its stored document copies from disk."""
        self._assets = [a for a in self._assets if a.asset_id != asset_id]
        self._tasks = [t for t in self._tasks if t.asset_id != asset_id]
        self._save()
        try:
            shutil.rmtree(_DOCUMENT_ROOT / asset_id, ignore_errors=True)
        except OSError:
            log.warning("Could not remove document folder for deleted asset '%s'.", asset_id)

    def get_asset(self, asset_id: str) -> Optional[MaintenanceAsset]:
        for asset in self._assets:
            if asset.asset_id == asset_id:
                return asset
        return None

    def all_assets(self) -> list[MaintenanceAsset]:
        return sorted(self._assets, key=lambda a: a.name.lower())

    # ------------------------------------------------------------------
    # Documents (receipts/warranties/manuals) — mirrors
    # core.trip_manager.TripManager's add_photo/remove_photo/photo_path
    # exactly, just renamed for this domain.
    # ------------------------------------------------------------------

    def add_document(self, asset_id: str, source_path: Path) -> str:
        """Copies an existing file into maintenance_documents/<asset_id>/
        and records its filename on the asset. Import-only (a file picker
        selects an existing receipt/manual/warranty PDF or image) — lets
        a copy failure (disk full, source vanished) propagate as OSError
        rather than silently no-op."""
        asset = self.get_asset(asset_id)
        if asset is None:
            raise ValueError(f"No maintenance asset with id '{asset_id}'.")

        asset_doc_dir = _DOCUMENT_ROOT / asset_id
        asset_doc_dir.mkdir(parents=True, exist_ok=True)
        destination = asset_doc_dir / source_path.name
        shutil.copy2(source_path, destination)

        if source_path.name not in asset.documents:
            asset.documents.append(source_path.name)
        self._save()
        return source_path.name

    def remove_document(self, asset_id: str, filename: str) -> MaintenanceAsset:
        """Removes the filename from the asset and deletes the stored copy (not the user's original, if any)."""
        asset = self.get_asset(asset_id)
        if asset is None:
            raise ValueError(f"No maintenance asset with id '{asset_id}'.")

        if filename in asset.documents:
            asset.documents.remove(filename)
            try:
                (_DOCUMENT_ROOT / asset_id / filename).unlink(missing_ok=True)
            except OSError:
                log.warning("Could not delete stored document copy for asset '%s': %s", asset_id, filename)

        self._save()
        return asset

    def document_path(self, asset_id: str, filename: str) -> Path:
        """Full on-disk path for an asset's stored document — for the UI to open/preview."""
        return _DOCUMENT_ROOT / asset_id / filename

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
        trigger_type: str = "calendar",
        meter_unit: str = "",
        meter_interval: Optional[float] = None,
        threshold_value: Optional[float] = None,
        threshold_direction: str = "below",
        auto_schedule: bool = False,
    ) -> MaintenanceTask:
        task = MaintenanceTask(
            task_id=uuid.uuid4().hex[:10],
            asset_id=asset_id,
            title=title,
            interval_days=interval_days,
            last_completed=last_completed,
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
            trigger_type=trigger_type,
            meter_unit=meter_unit,
            meter_interval=meter_interval,
            threshold_value=threshold_value,
            threshold_direction=threshold_direction,
            auto_schedule=auto_schedule,
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

    def mark_complete(
        self,
        task_id: str,
        completed_date: Optional[str] = None,
        meter_value: Optional[float] = None,
    ) -> MaintenanceTask:
        """For a meter-type task, meter_value sets the new
        last_completed_meter_value baseline (defaults to the latest
        logged reading for that task's series if omitted — None if
        nothing has been logged yet, which honestly leaves the task
        undue-computable until a reading exists)."""
        task = self.get_task(task_id)
        if task is None:
            raise ValueError(f"No maintenance task with id '{task_id}'.")
        task.last_completed = completed_date or date.today().isoformat()
        if task.is_meter_task:
            if meter_value is not None:
                task.last_completed_meter_value = meter_value
            else:
                task.last_completed_meter_value = _latest_reading_value(self.readings_for_task(task_id))
        self._save()
        log.info("Maintenance task completed: '%s' on %s", task.title, task.last_completed)
        # 2026-09-11 gamification pass — a real, distinct completion
        # event each call, including a recurring task's own legitimate
        # re-completion on schedule (same reasoning as a recurring
        # Bill's mark_bill_paid() below — re-granting XP each real
        # completion is correct, not a bug).
        grant_xp(self.context, 10, "\U0001F527 Task complete!", f"'{task.title}' is done.")
        return task

    # ------------------------------------------------------------------
    # Meter/sensor readings — thin wrapper around the shared Data Logger
    # service (core.data_logger_manager.DataLoggerManager). No new
    # storage here: a task's readings live in the same
    # data/data_logger_readings.json every other module already reads/
    # writes, keyed by this task's series_id.
    # ------------------------------------------------------------------

    def log_reading(self, task_id: str, value: float, unit: str = "", note: str = "") -> Reading:
        task = self.get_task(task_id)
        if task is None:
            raise ValueError(f"No maintenance task with id '{task_id}'.")
        return self.context.data_logger.add_reading(
            series_id=task.series_id, value=value, unit=unit or task.meter_unit, note=note
        )

    def readings_for_task(self, task_id: str) -> list[Reading]:
        task = self.get_task(task_id)
        if task is None:
            return []
        return self.context.data_logger.readings_for(task.series_id)

    # ------------------------------------------------------------------
    # Asset-level usage stats (fuel consumption, general odometer/hours
    # tracking, ...) — independent of any maintenance task's due-date
    # calculation. Named freely by the user (e.g. "Fuel", "Odometer");
    # same Data Logger series storage as task readings, just keyed by
    # asset + meter name instead of by task_id, so "how much fuel does
    # the mower use" is answerable even when no task is currently tied
    # to a fuel-based recurrence.
    # ------------------------------------------------------------------

    @staticmethod
    def _asset_series_id(asset_id: str, meter_name: str) -> str:
        return f"maintenance_asset_{asset_id}_{meter_name}"

    def log_asset_reading(self, asset_id: str, meter_name: str, value: float, unit: str = "", note: str = "") -> Reading:
        if self.get_asset(asset_id) is None:
            raise ValueError(f"No maintenance asset with id '{asset_id}'.")
        return self.context.data_logger.add_reading(
            series_id=self._asset_series_id(asset_id, meter_name), value=value, unit=unit, note=note
        )

    def asset_meter_names(self, asset_id: str) -> list[str]:
        """Every meter name this asset has at least one logged reading
        under, derived from Data Logger series ids rather than stored
        separately — same "a series exists implicitly the moment it has
        a reading" convention DataLoggerManager itself uses."""
        prefix = self._asset_series_id(asset_id, "")
        return sorted(
            series_id[len(prefix):] for series_id in self.context.data_logger.list_series() if series_id.startswith(prefix)
        )

    def asset_readings(self, asset_id: str, meter_name: str) -> list[Reading]:
        return self.context.data_logger.readings_for(self._asset_series_id(asset_id, meter_name))

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
