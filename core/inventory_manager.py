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
from core.data_recovery import notify_data_corruption

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_ITEMS_FILE = _DATA_DIR / "inventory_items.json"
# Multi-user pass (2026-09-14) — the "shared object + user relationship"
# pattern's second real application (see [[project_mia_multiuser_vision]]
# and core.kitchen_manager.RecipeUserStats' own docstring for the first,
# Recipes). InventoryItem itself stays shared/household, same as Recipe;
# this file holds one real per-adjustment event, the direct analog of
# kitchen_manager.MealLogEntry.
_USAGE_LOG_FILE = _DATA_DIR / "inventory_usage_log.json"


@dataclass
class InventoryItem:
    item_id: str
    name: str
    quantity: int = 0
    category: str = ""
    location: str = ""
    notes: str = ""
    updated_at: str = ""  # ISO datetime
    # Multi-user pass (2026-09-14) — who first added this item, same
    # "attribute the shared object's own creation" role
    # core.kitchen_manager.Recipe.unlocked_by_profile_id plays for
    # Recipes. None (every item added before this field existed, or
    # added with no active profile) means "unattributed" — a real,
    # valid state, not an error.
    added_by_profile_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "quantity": self.quantity,
            "category": self.category,
            "location": self.location,
            "notes": self.notes,
            "updated_at": self.updated_at,
            "added_by_profile_id": self.added_by_profile_id,
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
            added_by_profile_id=data.get("added_by_profile_id"),
        )


@dataclass
class InventoryUsageEntry:
    """One real quantity adjustment, attributed to whoever was active
    when it happened — the direct analog of
    core.kitchen_manager.MealLogEntry. `delta` is negative for real
    consumption ("used the last roll of paper towels") and positive
    for a restock; `times_used()`/`last_used()` below only count the
    negative ones, matching the household's actual question ("who's
    used it, how often") rather than every adjustment indiscriminately."""

    entry_id: str
    item_id: str
    delta: int
    profile_id: Optional[str] = None
    timestamp: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "item_id": self.item_id,
            "delta": self.delta,
            "profile_id": self.profile_id,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_dict(data: dict) -> "InventoryUsageEntry":
        return InventoryUsageEntry(
            entry_id=data.get("entry_id", uuid.uuid4().hex[:10]),
            item_id=data.get("item_id", ""),
            delta=data.get("delta", 0),
            profile_id=data.get("profile_id"),
            timestamp=data.get("timestamp", ""),
        )


class InventoryManager:
    def __init__(self, context: AppContext, data_dir: Optional[Path] = None) -> None:
        # Whose data: a household's own folder (core/personal_data.py), or data/ by default.
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._items_file = self.data_dir / "inventory_items.json" if data_dir is not None else _ITEMS_FILE
        self._usage_log_file = self.data_dir / "inventory_usage_log.json" if data_dir is not None else _USAGE_LOG_FILE
        self.context = context
        self._items: list[InventoryItem] = []
        self._usage_log: list[InventoryUsageEntry] = []
        self._load()
        self._load_usage_log()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._items_file.exists():
            self._items = []
            return
        try:
            raw = json.loads(self._items_file.read_text(encoding="utf-8"))
            self._items = [InventoryItem.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load inventory_items.json — starting with an empty list.")
            notify_data_corruption(self.context, "inventory_items.json")
            self._items = []

    def _load_usage_log(self) -> None:
        if not self._usage_log_file.exists():
            self._usage_log = []
            return
        try:
            raw = json.loads(self._usage_log_file.read_text(encoding="utf-8"))
            self._usage_log = [InventoryUsageEntry.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load inventory_usage_log.json — starting with an empty list.")
            notify_data_corruption(self.context, "inventory_usage_log.json")
            self._usage_log = []

    def reload(self) -> None:
        """Re-reads inventory_items.json from disk — see ExpeditionManager.reload()'s docstring for why."""
        self._load()
        self._load_usage_log()

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._items_file,
            json.dumps([i.to_dict() for i in self._items], indent=2),
            encoding="utf-8",
        )

    def _save_usage_log(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(
            self._usage_log_file,
            json.dumps([e.to_dict() for e in self._usage_log], indent=2),
            encoding="utf-8",
        )

    def _active_profile_id(self) -> Optional[str]:
        active_profile = self.context.profiles.get_active_profile() if self.context.profiles is not None else None
        return active_profile.profile_id if active_profile is not None else None

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
            added_by_profile_id=self._active_profile_id(),
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
        """Convenience for a quick +1/-1 button — clamps at 0 rather than
        going negative. Multi-user pass (2026-09-14) — a real, non-zero
        delta also appends an InventoryUsageEntry attributed to whoever's
        active, the direct analog of kitchen_manager.log_meal(). A
        clamped-to-0 delta (e.g. -1 on an item already at 0) still logs
        the attempt as a real -1 — that's still a real "someone tried to
        use this" event, not a no-op, even though the stored quantity
        itself doesn't go negative."""
        item = self.get_item(item_id)
        if item is None:
            raise ValueError(f"No inventory item with id '{item_id}'.")
        item.quantity = max(0, item.quantity + delta)
        item.updated_at = datetime.now().isoformat(timespec="seconds")
        if delta != 0:
            self._usage_log.append(InventoryUsageEntry(
                entry_id=uuid.uuid4().hex[:10],
                item_id=item_id,
                delta=delta,
                profile_id=self._active_profile_id(),
                timestamp=item.updated_at,
            ))
            self._save_usage_log()
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

    # ------------------------------------------------------------------
    # Usage (multi-user pass, 2026-09-14) — see InventoryUsageEntry's
    # own docstring; direct analog of kitchen_manager's
    # times_made()/last_made_date().
    # ------------------------------------------------------------------

    def usage_log_for_item(self, item_id: str) -> list[InventoryUsageEntry]:
        """Every real adjustment (both restocks and consumption) for
        this item, oldest first."""
        return [e for e in self._usage_log if e.item_id == item_id]

    def times_used(self, item_id: str, profile_id: Optional[str] = None) -> int:
        """Real consumption events only (delta < 0) — a restock isn't
        "using" the item. `profile_id=None` (the default) is the real
        household total (every profile's own usage, attributed or not).
        A real profile_id counts only entries attributed to that
        profile OR unattributed — same semantics
        core.kitchen_manager.KitchenManager.times_made() already
        established for the identical "shared object, per-user OR
        household view" question."""
        return sum(
            1 for e in self._usage_log
            if e.item_id == item_id and e.delta < 0
            and (profile_id is None or e.profile_id is None or e.profile_id == profile_id)
        )

    def last_used(self, item_id: str, profile_id: Optional[str] = None) -> Optional[InventoryUsageEntry]:
        """Same `profile_id` semantics as times_used() above. None if
        this item (or this profile's own slice of it) has never really
        been used.

        Picks the last MATCHING entry by real append order (self._usage_log
        is always appended to, never reordered), not by comparing
        `timestamp` strings — a real bug caught via an actual manual
        verification screenshot (2026-09-14): several quick adjustments
        can land in the same one-second-resolution timestamp, and
        `max(..., key=lambda e: e.timestamp)` breaks that tie by
        returning the FIRST one found (Python's max() is stable), the
        wrong direction for "most recent." List position is finer-
        grained than the timestamp string and always correct."""
        matches = [
            e for e in self._usage_log
            if e.item_id == item_id and e.delta < 0
            and (profile_id is None or e.profile_id is None or e.profile_id == profile_id)
        ]
        if not matches:
            return None
        return matches[-1]
