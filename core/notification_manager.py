"""
core.notification_manager
============================

A system-wide notification service any module can raise an alert
through — low battery, backup complete, a medication reminder, a
weather warning, etc. — without needing to know anything about how
notifications are displayed.

Design:
- Notifications are persisted to data/notifications.json, not just
  held in memory. A warning you didn't see before the device was shut
  off (e.g. "low battery") shouldn't silently vanish on restart.
- Raising a notification publishes a "notification.created" event on
  the shared EventBus. GUI components (the toast popup, the header
  bell count) subscribe to this rather than NotificationManager knowing
  anything about the GUI — same separation of concerns as every other
  core service in this project.
- Three severity levels only (info/warning/critical), matching the
  same vocabulary as Python's own logging levels conceptually, kept
  intentionally simple rather than building a whole priority system.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger
from core.at_rest import open_text
from core.atomic_write import atomic_write_text

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_NOTIFICATIONS_FILE = _DATA_DIR / "notifications.json"

VALID_LEVELS = ("info", "warning", "critical")


@dataclass
class Notification:
    """One notification: title, message, level (info, warning...), where it came from, when, and whether it's been
    read.
    """
    notification_id: str
    title: str
    message: str
    level: str = "info"
    source: str = "system"
    created_at: str = ""
    read: bool = False

    def to_dict(self) -> dict:
        """The notification as saved in notifications.json."""
        return {
            "notification_id": self.notification_id,
            "title": self.title,
            "message": self.message,
            "level": self.level,
            "source": self.source,
            "created_at": self.created_at,
            "read": self.read,
        }

    @staticmethod
    def from_dict(data: dict) -> "Notification":
        """A notification from its saved dict; missing fields take their defaults."""
        return Notification(
            notification_id=data.get("notification_id", uuid.uuid4().hex[:10]),
            title=data.get("title", ""),
            message=data.get("message", ""),
            level=data.get("level", "info"),
            source=data.get("source", "system"),
            created_at=data.get("created_at", ""),
            read=data.get("read", False),
        )


class NotificationManager:
    """The person's notifications (notifications.json in their folder, written through atomic_write_text). Raising one
    shows a toast and is kept; every change publishes notification.updated so screens refresh.
    """
    def __init__(self, context: AppContext, data_dir: Optional[Path] = None) -> None:
        # Whose data: a person's own folder (core/personal_data.py), or data/ by default.
        """Points at the person's file (data/ by default) and loads it."""
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._notifications_file = self.data_dir / "notifications.json" if data_dir is not None else _NOTIFICATIONS_FILE
        self.context = context
        self._notifications: list[Notification] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Reads the notifications; a damaged file starts empty and says so with a notification of its own (it can't use
        notify_data_corruption: the context doesn't have this manager yet). Sealed at rest (DEC-0126): a sealed file is opened, one that won't open is copied aside and starts empty.
        """
        if not self._notifications_file.exists():
            self._notifications = []
            return
        try:
            raw = json.loads(open_text(self._notifications_file))
            self._notifications = [Notification.from_dict(d) for d in raw]
        except (ValueError, OSError):  # ValueError: bad JSON or a sealed file that won't open
            log.exception("Failed to load notifications.json — starting with an empty list.")
            self._notifications = []
            # Self-reference, not core.data_recovery.notify_data_corruption()
            # (2026-09-14 stabilization pass) — self.context.notifications
            # isn't assigned until AFTER this constructor returns (see
            # core/application.py), but self.notify() is a normal, fully
            # usable instance method the moment self._notifications above
            # is set, one line up.
            self.notify(
                title="⚠️ Data file recovered",
                message="'notifications.json' couldn't be read and has been reset to empty. See logs/mia.log for detail.",
                level="warning",
                source="system",
            )

    def _save(self) -> None:
        """Writes every notification atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._notifications_file,
            json.dumps([n.to_dict() for n in self._notifications], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Raising notifications
    # ------------------------------------------------------------------

    def notify(self, title: str, message: str, level: str = "info", source: str = "system",
               always: bool = False) -> Optional[Notification]:
        """
        Raise a new notification. Any module can call this via
        self.context.notifications.notify(...) — no registration needed.

        2026-07-15 "ForMIA" design handoff, Quick Bus widget: returns
        None (no notification created, persisted, or published) when
        `notifications.enabled` is false — a real behind-the-scenes
        effect for that dashboard toggle, not just a cosmetic switch.
        No existing caller inspects the return value (checked before
        this change), so this is safe.
        """
        # `always`: a safety escalation (core/safety_escalation.py) gets
        # through even with notifications switched off.
        if not always and not self.context.config.get("notifications.enabled", True):
            log.info("Notification suppressed (notifications disabled) [%s] from '%s': %s", level, source, title)
            return None

        if level not in VALID_LEVELS:
            log.warning("Unknown notification level '%s' from '%s' — defaulting to 'info'.", level, source)
            level = "info"

        notification = Notification(
            notification_id=uuid.uuid4().hex[:10],
            title=title,
            message=message,
            level=level,
            source=source,
            created_at=datetime.now().isoformat(timespec="seconds"),
            read=False,
        )
        self._notifications.insert(0, notification)  # newest first
        self._save()
        log.info("Notification raised [%s] from '%s': %s", level, source, title)
        # Whose notification (accounts, 2026-10-01): a person's own list
        # (core/personal_data.py) tells the desktop and the phone push
        # relay, so a toast or push only reaches that person.
        self.context.events.publish("notification.created", notification=notification,
                                    profile_id=getattr(self.context, "profile_id", None))
        return notification

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def list_all(self) -> list[Notification]:
        """Every notification."""
        return list(self._notifications)

    def list_unread(self) -> list[Notification]:
        """The notifications not read yet."""
        return [n for n in self._notifications if not n.read]

    def unread_count(self) -> int:
        """How many haven't been read."""
        return len(self.list_unread())

    # ------------------------------------------------------------------
    # Managing state
    # ------------------------------------------------------------------

    def mark_all_read(self) -> None:
        """Marks every notification read."""
        for n in self._notifications:
            n.read = True
        self._save()
        self.context.events.publish("notification.updated")

    def dismiss(self, notification_id: str) -> None:
        """Dismisses one notification on purpose, publishing notification.dismissed so the communication gate learns
        from it.
        """
        self._notifications = [n for n in self._notifications if n.notification_id != notification_id]
        self._save()
        # The owner closed this one on purpose (not "clear all"): the
        # communication gate learns from it (core/communication_gate.py).
        self.context.events.publish("notification.dismissed", notification_id=notification_id)
        self.context.events.publish("notification.updated")

    def clear_all(self) -> None:
        """Clears every notification (not counted as dismissing each one)."""
        self._notifications = []
        self._save()
        self.context.events.publish("notification.updated")
