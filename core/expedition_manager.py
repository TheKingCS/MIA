"""
core.expedition_manager
==========================

Top-level container for an Expedition Mode outing — docs/ROADMAP.md
milestone 12.1. A single Expedition (e.g. a long weekend spent in one
area) can hold multiple core.trip_manager.Trip records — one per
activity/leg (e.g. Saturday's hike-in, Sunday's fishing trip, both under
one Expedition). Same persisted-JSON pattern as core/waypoint_manager.py:
data/expeditions.json, a dataclass with to_dict/from_dict, a manager
class wrapping load/save.

Deleting an Expedition unlinks (does not cascade-delete) its Trips —
consistent with this project's non-destructive bias elsewhere (e.g.
delete/adjust actions in core/inventory_manager.py never silently take
out other records); a Trip whose expedition_id no longer resolves just
stops showing up under any Expedition, but isn't deleted itself.
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
from core.data_recovery import notify_data_corruption

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_EXPEDITIONS_FILE = _DATA_DIR / "expeditions.json"


@dataclass
class Expedition:
    expedition_id: str
    name: str
    start_date: str = ""  # ISO date
    end_date: str = ""
    location: str = ""  # freeform region/area name
    notes: str = ""
    created_at: str = ""  # ISO datetime
    updated_at: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "expedition_id": self.expedition_id,
            "name": self.name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "location": self.location,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Expedition":
        return Expedition(
            expedition_id=data.get("expedition_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            start_date=data.get("start_date", ""),
            end_date=data.get("end_date", ""),
            location=data.get("location", ""),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class ExpeditionManager:
    def __init__(self, context: AppContext, data_dir: Optional[Path] = None) -> None:
        # Whose data: a household's own folder (core/personal_data.py), or data/ by default.
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._expeditions_file = self.data_dir / "expeditions.json" if data_dir is not None else _EXPEDITIONS_FILE
        self.context = context
        self._expeditions: list[Expedition] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._expeditions_file.exists():
            self._expeditions = []
            return
        try:
            raw = json.loads(self._expeditions_file.read_text(encoding="utf-8"))
            self._expeditions = [Expedition.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load expeditions.json — starting with an empty list.")
            notify_data_corruption(self.context, "expeditions.json")
            self._expeditions = []

    def reload(self) -> None:
        """
        Re-reads expeditions.json from disk, discarding in-memory state.
        docs/ROADMAP.md milestone v0.19 (Home Dock auto-launch
        Dashboard) — an auto-import needs its results visible
        immediately, not after a manual app restart the way
        core/expedition_sync.py's docstring otherwise requires.
        """
        self._load()

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._expeditions_file,
            json.dumps([e.to_dict() for e in self._expeditions], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def add_expedition(
        self,
        name: str,
        start_date: str = "",
        end_date: str = "",
        location: str = "",
        notes: str = "",
    ) -> Expedition:
        now = datetime.now().isoformat(timespec="seconds")
        expedition = Expedition(
            expedition_id=uuid.uuid4().hex[:10],
            name=name,
            start_date=start_date,
            end_date=end_date,
            location=location,
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        self._expeditions.append(expedition)
        self._save()
        log.info("Expedition added: '%s'", name)
        return expedition

    def update_expedition(self, expedition_id: str, **fields) -> Expedition:
        expedition = self.get_expedition(expedition_id)
        if expedition is None:
            raise ValueError(f"No expedition with id '{expedition_id}'.")
        for key, value in fields.items():
            if key == "created_at":
                raise ValueError("'created_at' can't be set through update_expedition().")
            if not hasattr(expedition, key):
                raise ValueError(f"Expedition has no field '{key}'.")
            setattr(expedition, key, value)
        expedition.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return expedition

    def delete_expedition(self, expedition_id: str) -> None:
        self._expeditions = [e for e in self._expeditions if e.expedition_id != expedition_id]
        self._save()

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_expedition(self, expedition_id: str) -> Optional[Expedition]:
        for expedition in self._expeditions:
            if expedition.expedition_id == expedition_id:
                return expedition
        return None

    def all_expeditions(self) -> list[Expedition]:
        return sorted(self._expeditions, key=lambda e: e.start_date)
