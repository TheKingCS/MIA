"""
core.inventory_manager
=========================

Backs the Inventory tool (modules/toolbox/tools/inventory_tool.py) —
milestone 3.5 in docs/ROADMAP.md. Same persisted-JSON pattern as
core.calendar_manager.CalendarManager / core.alarm_manager.AlarmManager:
data/inventory_items.json, a dataclass with to_dict/from_dict, a
manager class wrapping load/save. Lives in core/ for the same reason
those two do — only core/ services write to data/, which is also what
lets backup_manager.py's data/ rglob pick this up automatically with
no backup/restore code changes.

Unlike Calendar/Alarm/Journal, Inventory isn't listed in
docs/ROADMAP.md's "Shared core services" table — it's a single
Toolbox feature (like Alarm/Stopwatch), not infrastructure other
modules are expected to reuse. It still gets a core/ manager rather
than living inside modules/toolbox/ because the "only core/ writes to
data/" convention is about where persistence lives, not about how many
modules use a given service.
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
_ITEMS_FILE = _DATA_DIR / "inventory_items.json"


@dataclass
class InventoryItem:
    item_id: str
    name: str
    quantity: int = 0
    category: str = ""
    location: str = ""
    notes: str = ""
    updated_at: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "quantity": self.quantity,
            "category": self.category,
            "location": self.location,
            "notes": self.notes,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "InventoryItem":
        return InventoryItem(
            item_id=data.get("item_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            quantity=data.get("quantity", 0),
            category=data.get("category", ""),
            location=data.get("location", ""),
            notes=data.get("notes", ""),
            updated_at=data.get("updated_at", ""),
        )


class InventoryManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._items: list[InventoryItem] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _ITEMS_FILE.exists():
            self._items = []
            return
        try:
            raw = json.loads(_ITEMS_FILE.read_text(encoding="utf-8"))
            self._items = [InventoryItem.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load inventory_items.json — starting with an empty list.")
            self._items = []

    def reload(self) -> None:
        """Re-reads inventory_items.json from disk — see ExpeditionManager.reload()'s docstring for why."""
        self._load()

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_ITEMS_FILE,
            json.dumps([i.to_dict() for i in self._items], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def add_item(
        self,
        name: str,
        quantity: int = 0,
        category: str = "",
        location: str = "",
        notes: str = "",
    ) -> InventoryItem:
        item = InventoryItem(
            item_id=uuid.uuid4().hex[:10],
            name=name,
            quantity=max(0, quantity),
            category=category,
            location=location,
            notes=notes,
            updated_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._items.append(item)
        self._save()
        log.info("Inventory item added: '%s' (qty %d)", name, item.quantity)
        return item

    def update_item(self, item_id: str, **fields) -> InventoryItem:
        item = self.get_item(item_id)
        if item is None:
            raise ValueError(f"No inventory item with id '{item_id}'.")
        for key, value in fields.items():
            if key == "updated_at":
                raise ValueError("'updated_at' can't be set through update_item().")
            if not hasattr(item, key):
                raise ValueError(f"InventoryItem has no field '{key}'.")
            setattr(item, key, value)
        if item.quantity < 0:
            item.quantity = 0
        item.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return item

    def adjust_quantity(self, item_id: str, delta: int) -> InventoryItem:
        """Convenience for a quick +1/-1 button — clamps at 0 rather than going negative."""
        item = self.get_item(item_id)
        if item is None:
            raise ValueError(f"No inventory item with id '{item_id}'.")
        item.quantity = max(0, item.quantity + delta)
        item.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return item

    def delete_item(self, item_id: str) -> None:
        self._items = [i for i in self._items if i.item_id != item_id]
        self._save()

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_item(self, item_id: str) -> Optional[InventoryItem]:
        for item in self._items:
            if item.item_id == item_id:
                return item
        return None

    def all_items(self) -> list[InventoryItem]:
        return sorted(self._items, key=lambda i: i.name.lower())

    def search(self, query: str) -> list[InventoryItem]:
        """Case-insensitive substring match over name, category, location, and notes."""
        query_lower = query.strip().lower()
        if not query_lower:
            return []

        matches = []
        for item in self._items:
            haystack = f"{item.name} {item.category} {item.location} {item.notes}".lower()
            if query_lower in haystack:
                matches.append(item)
        return sorted(matches, key=lambda i: i.name.lower())
