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
from core.atomic_write import atomic_write_text

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_NOTIFICATIONS_FILE = _DATA_DIR / "notifications.json"

VALID_LEVELS = ("info", "warning", "critical")


@dataclass
class Notification:
    notification_id: str
    title: str
    message: str
    level: str = "info"
    source: str = "system"
    created_at: str = ""
    read: bool = False

    def to_dict(self) -> dict:
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
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._notifications: list[Notification] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _NOTIFICATIONS_FILE.exists():
            self._notifications = []
            return
        try:
            raw = json.loads(_NOTIFICATIONS_FILE.read_text(encoding="utf-8"))
            self._notifications = [Notification.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load notifications.json — starting with an empty list.")
            self._notifications = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_NOTIFICATIONS_FILE,
            json.dumps([n.to_dict() for n in self._notifications], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Raising notifications
    # ------------------------------------------------------------------

    def notify(self, title: str, message: str, level: str = "info", source: str = "system") -> Optional[Notification]:
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
        if not self.context.config.get("notifications.enabled", True):
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
        self.context.events.publish("notification.created", notification=notification)
        return notification

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def list_all(self) -> list[Notification]:
        return list(self._notifications)

    def list_unread(self) -> list[Notification]:
        return [n for n in self._notifications if not n.read]

    def unread_count(self) -> int:
        return len(self.list_unread())

    # ------------------------------------------------------------------
    # Managing state
    # ------------------------------------------------------------------

    def mark_all_read(self) -> None:
        for n in self._notifications:
            n.read = True
        self._save()
        self.context.events.publish("notification.updated")

    def dismiss(self, notification_id: str) -> None:
        self._notifications = [n for n in self._notifications if n.notification_id != notification_id]
        self._save()
        self.context.events.publish("notification.updated")

    def clear_all(self) -> None:
        self._notifications = []
        self._save()
        self.context.events.publish("notification.updated")
