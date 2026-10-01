"""
core.journal_manager
=======================

Backs the Notes module (modules/notes/module.py) — milestone 3.4 in
docs/ROADMAP.md, which upgrades that module from a placeholder into
the "Notes/Journal Engine" described in ROADMAP.md's shared core
services table: dated, searchable, taggable entries. It's a core/
service (not module-local) specifically because that table lists it
as shared infrastructure future modules (Project Manager notes, Lab
notes, vehicle notes) are meant to reuse via their own
self.context.journal calls — same reasoning as
core.calculator_engine.CalculatorEngine being built as a shared
service from its first two calculators, not a Unit-Converter-only
class. Voice memo transcription (also listed in that table) is out of
scope — no STT exists anywhere in the app yet; that's an Assistant
(v0.5) capability.

Same persisted-JSON pattern as core.calendar_manager.CalendarManager:
data/journal_entries.json, a dataclass with to_dict/from_dict, a
manager class wrapping load/save.

`trip_id`/`conditions` (docs/ROADMAP.md milestone 12.4, Trip Log) are
additive, optional fields: an entry with neither set behaves exactly as
before. `trip_id` links an entry to a core.trip_manager.Trip (surfaced
in that trip's detail view via `entries_for_trip()`); `conditions` is a
first-class weather/conditions field, not folded into `body`, so a
trip's logged weather stays queryable/structured rather than buried in
free text.
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
from core.data_recovery import notify_data_corruption

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_ENTRIES_FILE = _DATA_DIR / "journal_entries.json"


@dataclass
class JournalEntry:
    entry_id: str
    title: str
    body: str = ""
    tags: list[str] = field(default_factory=list)
    trip_id: Optional[str] = None
    conditions: str = ""  # weather/conditions, e.g. "Clear, ~15C, light wind"
    created_at: str = ""  # ISO datetime
    updated_at: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "title": self.title,
            "body": self.body,
            "tags": self.tags,
            "trip_id": self.trip_id,
            "conditions": self.conditions,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "JournalEntry":
        return JournalEntry(
            entry_id=data.get("entry_id", uuid.uuid4().hex[:10]),
            title=data.get("title", ""),
            body=data.get("body", ""),
            tags=list(data.get("tags", [])),
            trip_id=data.get("trip_id"),
            conditions=data.get("conditions", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class JournalManager:
    def __init__(self, context: AppContext, data_dir: Optional[Path] = None) -> None:
        # Whose data: a person's own folder (core/personal_data.py), or the
        # shared data/ folder by default.
        self.data_dir = Path(data_dir) if data_dir is not None else _ENTRIES_FILE.parent
        self._entries_file = self.data_dir / _ENTRIES_FILE.name if data_dir is not None else _ENTRIES_FILE
        self.context = context
        self._entries: list[JournalEntry] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._entries_file.exists():
            self._entries = []
            return
        try:
            raw = json.loads(self._entries_file.read_text(encoding="utf-8"))
            self._entries = [JournalEntry.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load journal_entries.json — starting with an empty list.")
            notify_data_corruption(self.context, "journal_entries.json")
            self._entries = []

    def reload(self) -> None:
        """Re-reads journal_entries.json from disk — see ExpeditionManager.reload()'s docstring for why."""
        self._load()

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._entries_file,
            json.dumps([e.to_dict() for e in self._entries], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def add_entry(
        self,
        title: str,
        body: str = "",
        tags: Optional[list[str]] = None,
        trip_id: Optional[str] = None,
        conditions: str = "",
    ) -> JournalEntry:
        now = datetime.now().isoformat(timespec="seconds")
        entry = JournalEntry(
            entry_id=uuid.uuid4().hex[:10],
            title=title,
            body=body,
            tags=list(tags) if tags else [],
            trip_id=trip_id,
            conditions=conditions,
            created_at=now,
            updated_at=now,
        )
        self._entries.append(entry)
        self._save()
        log.info("Journal entry added: '%s'", title)
        return entry

    def update_entry(self, entry_id: str, **fields) -> JournalEntry:
        """
        `entry_id` itself can never appear in **fields — it's already
        bound by the positional parameter above, so passing
        entry_id=... as a keyword raises a plain TypeError at the call
        site before this body even runs. Only created_at/updated_at
        need an explicit guard here.
        """
        entry = self.get_entry(entry_id)
        if entry is None:
            raise ValueError(f"No journal entry with id '{entry_id}'.")
        for key, value in fields.items():
            if key in ("created_at", "updated_at"):
                raise ValueError(f"'{key}' can't be set through update_entry().")
            if not hasattr(entry, key):
                raise ValueError(f"JournalEntry has no field '{key}'.")
            setattr(entry, key, value)
        entry.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return entry

    def delete_entry(self, entry_id: str) -> None:
        self._entries = [e for e in self._entries if e.entry_id != entry_id]
        self._save()

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_entry(self, entry_id: str) -> Optional[JournalEntry]:
        for entry in self._entries:
            if entry.entry_id == entry_id:
                return entry
        return None

    def all_entries(self) -> list[JournalEntry]:
        """Newest-updated first — matches how a journal is naturally browsed."""
        return sorted(self._entries, key=lambda e: e.updated_at, reverse=True)

    def entries_for_trip(self, trip_id: str) -> list[JournalEntry]:
        """Newest-updated first, same ordering as all_entries()."""
        return sorted(
            (e for e in self._entries if e.trip_id == trip_id),
            key=lambda e: e.updated_at,
            reverse=True,
        )

    def search(self, query: str) -> list[JournalEntry]:
        """Case-insensitive substring match over title, body, and tags."""
        query_lower = query.strip().lower()
        if not query_lower:
            return []

        matches = []
        for entry in self._entries:
            haystack = f"{entry.title} {entry.body} {' '.join(entry.tags)}".lower()
            if query_lower in haystack:
                matches.append(entry)
        return sorted(matches, key=lambda e: e.updated_at, reverse=True)
