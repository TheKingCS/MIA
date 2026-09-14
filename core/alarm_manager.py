"""
core.alarm_manager
=====================

Backs the Alarm tool (modules/toolbox/tools/alarm_tool.py) — persisted
to data/alarms.json, same durability pattern as
core.calendar_manager.CalendarManager.

Unlike Calendar, Alarm needs to actually *do* something at the right
moment even when the user is elsewhere in the app (not looking at the
Alarm screen). Rather than build a bespoke alert UI, a due alarm is
raised through the existing core.notification_manager.NotificationManager
— MIAApplication owns a periodic QTimer (see core/application.py) that
calls check_due() every ~20s and turns any fired Alarm into a regular
notification, which the existing toast popup / Notification Center
already know how to display, regardless of which module is on screen.

check_due() takes `now` as a parameter (rather than calling
datetime.now() itself) specifically so it's unit-testable with a fixed
clock, without any real waiting or Qt timer involved — see
tests/test_alarm_manager.py.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger
from core.atomic_write import atomic_write_text

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_ALARMS_FILE = _DATA_DIR / "alarms.json"


@dataclass
class Alarm:
    alarm_id: str
    label: str
    time: str  # "HH:MM", 24-hour
    days: list[int] = field(default_factory=list)  # 0=Mon..6=Sun; empty = one-time
    enabled: bool = True
    last_triggered: Optional[str] = None  # ISO "YYYY-MM-DD" of the last date this alarm fired

    def to_dict(self) -> dict:
        return {
            "alarm_id": self.alarm_id,
            "label": self.label,
            "time": self.time,
            "days": self.days,
            "enabled": self.enabled,
            "last_triggered": self.last_triggered,
        }

    @staticmethod
    def from_dict(data: dict) -> "Alarm":
        return Alarm(
            alarm_id=data.get("alarm_id", uuid.uuid4().hex[:10]),
            label=data.get("label", ""),
            time=data.get("time", "00:00"),
            days=list(data.get("days", [])),
            enabled=data.get("enabled", True),
            last_triggered=data.get("last_triggered"),
        )


class AlarmManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._alarms: list[Alarm] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _ALARMS_FILE.exists():
            self._alarms = []
            return
        try:
            raw = json.loads(_ALARMS_FILE.read_text(encoding="utf-8"))
            self._alarms = [Alarm.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load alarms.json — starting with an empty list.")
            self._alarms = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_ALARMS_FILE,
            json.dumps([a.to_dict() for a in self._alarms], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def add_alarm(self, label: str, time: str, days: Optional[list[int]] = None) -> Alarm:
        alarm = Alarm(
            alarm_id=uuid.uuid4().hex[:10],
            label=label,
            time=time,
            days=list(days) if days else [],
        )
        self._alarms.append(alarm)
        self._save()
        log.info("Alarm added: '%s' at %s", label, time)
        return alarm

    def update_alarm(self, alarm_id: str, **fields) -> Alarm:
        alarm = self.get_alarm(alarm_id)
        if alarm is None:
            raise ValueError(f"No alarm with id '{alarm_id}'.")
        for key, value in fields.items():
            if not hasattr(alarm, key):
                raise ValueError(f"Alarm has no field '{key}'.")
            setattr(alarm, key, value)
        self._save()
        return alarm

    def delete_alarm(self, alarm_id: str) -> None:
        self._alarms = [a for a in self._alarms if a.alarm_id != alarm_id]
        self._save()

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_alarm(self, alarm_id: str) -> Optional[Alarm]:
        for alarm in self._alarms:
            if alarm.alarm_id == alarm_id:
                return alarm
        return None

    def all_alarms(self) -> list[Alarm]:
        return list(self._alarms)

    # ------------------------------------------------------------------
    # Triggering
    # ------------------------------------------------------------------

    def check_due(self, now: datetime) -> list[Alarm]:
        """
        Fire (raise a notification for) every enabled alarm whose time
        matches `now`'s HH:MM, on an allowed day, that hasn't already
        fired today. One-time alarms (no `days`) auto-disable after
        firing; repeating alarms just record `last_triggered` so they
        fire once per matching day, not on every poll within that
        minute. Returns the list of alarms that fired.
        """
        current_time = now.strftime("%H:%M")
        today = now.strftime("%Y-%m-%d")
        fired: list[Alarm] = []

        for alarm in self._alarms:
            if not alarm.enabled:
                continue
            if alarm.time != current_time:
                continue
            if alarm.last_triggered == today:
                continue
            if alarm.days and now.weekday() not in alarm.days:
                continue

            alarm.last_triggered = today
            if not alarm.days:
                alarm.enabled = False
            fired.append(alarm)

            if self.context.notifications is not None:
                self.context.notifications.notify(
                    title=f"Alarm: {alarm.label}" if alarm.label else "Alarm",
                    message=f"It's {alarm.time}.",
                    level="warning",
                    source="alarm",
                )

        if fired:
            self._save()
        return fired
