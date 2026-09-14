"""
core.activity_log_manager
============================

The Activity/Memory Log shared service — docs/ROADMAP.md milestone
9.1, the "Activity/Memory Log (system-wide event history via the
event bus)" row of the shared core services table (used by the
Memories section, "what did I do on Project X" queries, Diagnostics
history).

Subscribes to a curated subset of events already published elsewhere
in the app — `module.opened`, `notification.created`,
`profile.switched` — rather than every event on the bus.
`menu.shown`/`modules.rescanned`/etc. are noise for a "what did I do"
memory feature, not signal; a curated subset keeps this useful and
keeps `data/activity_log.json` from filling up with entries nobody
would ever want summarized back to them.

Same persisted-JSON pattern as core/inventory_manager.py, with one
difference: entries are capped at `_MAX_ENTRIES` (oldest dropped
first) so a long-running kiosk device's log file doesn't grow
unbounded — this is an append-heavy, read-rarely log, not a dataset a
user curates by hand like Inventory/Notes.

docs/ROADMAP.md's own "Top-level module sections" note is explicit
that Memories is **not** a menu section — "Character, Memories, and
Global Search are system-wide / ambient" — so there is deliberately no
`modules/memories/` UI here. The query surface is
`core/assistant_actions.py`'s `recall_recent_activity` action
(milestone 9.2), which lets the Assistant answer "what have I been
doing" style questions using this log as raw material.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from core.app_context import AppContext
from core.logger import get_logger
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_ACTIVITY_LOG_FILE = _DATA_DIR / "activity_log.json"
_MAX_ENTRIES = 5000


@dataclass
class ActivityLogEntry:
    entry_id: str
    event_type: str
    summary: str
    timestamp: str  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "event_type": self.event_type,
            "summary": self.summary,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_dict(data: dict) -> "ActivityLogEntry":
        return ActivityLogEntry(
            entry_id=data.get("entry_id", uuid.uuid4().hex[:10]),
            event_type=data.get("event_type", ""),
            summary=data.get("summary", ""),
            timestamp=data.get("timestamp", ""),
        )


class ActivityLogManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._entries: list[ActivityLogEntry] = []
        self._module_lister: Optional[Callable[[], list]] = None
        self._load()

        self.context.events.subscribe("module.opened", self._on_module_opened)
        self.context.events.subscribe("notification.created", self._on_notification_created)
        self.context.events.subscribe("profile.switched", self._on_profile_switched)

    def register_module_lister(self, lister: Callable[[], list]) -> None:
        """
        `lister` returns the currently discovered modules (duck-typed:
        needs .module_id/.display_name) — same registration-callback
        shape as core/device_help_manager.py's register_module_lister,
        used here only for a nicer display_name in module-open log
        summaries. Not a hard dependency: falls back to the raw
        module_id if never registered or the lookup fails.
        """
        self._module_lister = lister

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _ACTIVITY_LOG_FILE.exists():
            self._entries = []
            return
        try:
            raw = json.loads(_ACTIVITY_LOG_FILE.read_text(encoding="utf-8"))
            self._entries = [ActivityLogEntry.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load activity_log.json — starting with an empty list.")
            notify_data_corruption(self.context, "activity_log.json")
            self._entries = []

    def _save(self) -> None:
        # Full-file rewrite per entry, same as every other persisted-JSON
        # manager in this codebase (Inventory, Notes, Alarms). Accepted
        # here too: real usage logs at most a few dozen events/day, so
        # reaching _MAX_ENTRIES worth of file size to rewrite takes
        # months, not something a tight loop would ever produce outside
        # of a synthetic stress test (see this rewrite cost hit directly
        # in tests/test_activity_log_manager.py's capping test before it
        # was rescoped to a small cap).
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_ACTIVITY_LOG_FILE,
            json.dumps([e.to_dict() for e in self._entries], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def _log(self, event_type: str, summary: str) -> ActivityLogEntry:
        entry = ActivityLogEntry(
            entry_id=uuid.uuid4().hex[:10],
            event_type=event_type,
            summary=summary,
            timestamp=datetime.now().isoformat(timespec="seconds"),
        )
        self._entries.append(entry)
        if len(self._entries) > _MAX_ENTRIES:
            self._entries = self._entries[-_MAX_ENTRIES:]
        self._save()
        return entry

    # ------------------------------------------------------------------
    # Event subscribers
    # ------------------------------------------------------------------

    def _on_module_opened(self, module_id: str) -> None:
        display_name = self._display_name_for(module_id)
        self._log("module.opened", f"Opened the {display_name} module.")

    def _on_notification_created(self, notification) -> None:
        self._log("notification.created", f'Notification: "{notification.title}" — {notification.message}')

    def _on_profile_switched(self, profile_id: str) -> None:
        name = profile_id
        if self.context.profiles is not None:
            match = next((p for p in self.context.profiles.list_profiles() if p.profile_id == profile_id), None)
            if match is not None:
                name = match.name
        self._log("profile.switched", f"Switched to profile '{name}'.")

    def _display_name_for(self, module_id: str) -> str:
        """Best-effort display_name lookup via the registered module lister — falls back to the raw module_id."""
        if self._module_lister is None:
            return module_id
        try:
            for module in self._module_lister():
                if module.module_id == module_id:
                    return module.display_name
        except Exception:
            log.exception("Module lookup failed while logging activity for '%s'.", module_id)
        return module_id

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def recent(self, limit: int = 20) -> list[ActivityLogEntry]:
        """Most recent entries first."""
        return list(reversed(self._entries[-limit:]))

    def search(self, query: str, limit: int = 20) -> list[ActivityLogEntry]:
        """Case-insensitive substring match over summary/event_type, most recent first."""
        query_lower = query.strip().lower()
        if not query_lower:
            return []
        matches = [e for e in self._entries if query_lower in e.summary.lower() or query_lower in e.event_type.lower()]
        return list(reversed(matches[-limit:]))
