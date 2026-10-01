"""
core.online_watch
====================

Offline awareness follow-ups (2026-09-28), on top of
core/connectivity.py:

1. **Telling the owner when MIA goes offline or comes back.** `OnlineWatch`
   turns the monitor's readings into transitions, only after two
   readings in a row agree, so a single dropped probe isn't news. The
   app offers them through the communication gate (at most one of each
   a day, by fingerprint).
2. **"Remind me when I'm back online."** The system prompt already tells
   MIA to offer this while offline; `OnlineReminders` makes it real: a
   small saved list (data/online_reminders.json), delivered as ordinary
   notifications the moment the connection returns (the owner asked for
   them, so they don't count against the daily limit).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.assistant_actions import AssistantAction
from core.atomic_write import atomic_write_text
from core.connectivity import OFFLINE, ONLINE, UNKNOWN
from core.data_recovery import notify_data_corruption
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_REMINDERS_FILE = _DATA_DIR / "online_reminders.json"

WENT_OFFLINE, CAME_BACK = "went_offline", "came_back"


class OnlineWatch:
    """Pure logic. Feed it readings; it reports a settled change."""

    def __init__(self, confirm: int = 2) -> None:
        self._confirm = confirm
        self._settled: Optional[str] = None
        self._candidate: Optional[str] = None
        self._count = 0

    def observe(self, status: str) -> Optional[str]:
        if status not in (ONLINE, OFFLINE):
            return None  # "unknown" is no news
        if status == self._settled:
            self._candidate, self._count = None, 0
            return None
        if status != self._candidate:
            self._candidate, self._count = status, 0
        self._count += 1
        if self._count < self._confirm:
            return None
        previous, self._settled = self._settled, status
        self._candidate, self._count = None, 0
        if previous is None:
            return None  # the first settled reading after boot isn't a change
        return WENT_OFFLINE if status == OFFLINE else CAME_BACK


def transition_message(kind: str, waiting: int) -> tuple[str, str]:
    """Pure logic. (title, message) for the notice."""
    if kind == WENT_OFFLINE:
        return ("\U0001F4F6 Offline", "I've lost the internet connection. Everything here still works; bank sync, "
                "phone notifications and new map downloads wait until it's back.")
    extra = f" I have {waiting} reminder{'s' if waiting != 1 else ''} for you." if waiting else ""
    return ("\U0001F4F6 Back online", "The internet connection is back." + extra)


class OnlineReminders:
    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        # Whose data: a person's own folder (core/personal_data.py), or the
        # shared data/ folder by default.
        self.data_dir = Path(data_dir) if data_dir is not None else _REMINDERS_FILE.parent
        self._reminders_file = self.data_dir / _REMINDERS_FILE.name if data_dir is not None else _REMINDERS_FILE
        self.context = context
        self._items: list[dict] = []
        if self._reminders_file.exists():
            try:
                self._items = list(json.loads(self._reminders_file.read_text(encoding="utf-8")))
            except (OSError, ValueError, TypeError):
                log.exception("online_reminders.json unreadable, starting empty.")
                notify_data_corruption(context, "online_reminders.json")

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._reminders_file, json.dumps(self._items, indent=2))

    def add(self, what: str) -> None:
        self._items.append({"what": what.strip(), "created": datetime.now().isoformat(timespec="seconds")})
        self._save()

    def pending(self) -> list[str]:
        return [item["what"] for item in self._items]

    def take_all(self) -> list[str]:
        """The reminders, removed: they're being delivered now."""
        items, self._items = self.pending(), []
        if items:
            self._save()
        return items


def _action_remind_when_online(context, arguments: dict) -> str:
    what = str(arguments.get("what") or "").strip()
    reminders = getattr(context, "online_reminders", None)
    if not what:
        return "What should I remind you about when we're back online?"
    if reminders is None:
        return "I can't keep online reminders right now."
    monitor = getattr(context, "connectivity", None)
    reminders.add(what)
    if monitor is not None and monitor.status == ONLINE:
        return f"We're actually online right now, so go ahead. I've noted it anyway: {what}."
    return f"Okay, I'll remind you as soon as the internet is back: {what}."


def remind_when_online_action() -> AssistantAction:
    return AssistantAction(
        name="remind_when_online", domain="system",
        description="Remind the user about something as soon as MIA's internet connection is back "
                    "(e.g. sync the bank, send a photo). Use when they ask for that while offline.",
        parameters={"type": "object", "properties": {
            "what": {"type": "string", "description": "What to remind them about, e.g. 'sync the bank accounts'."},
        }, "required": ["what"]},
        handler=_action_remind_when_online,
        trigger_phrases=("when i'm back online", "when we're back online", "when you're back online", "when the internet",
                         "back online", "when we have internet", "once we're online", "when i have signal"),
    )
