"""
core.component_manager
=========================

Backs the Component DB (modules/workshop/module.py) — docs/ROADMAP.md
milestone 8.3. Same persisted-JSON pattern as
core/inventory_manager.py: data/components.json, a dataclass with
to_dict/from_dict, a manager class wrapping load/save.

Deliberately a separate manager/dataset from core/inventory_manager.py's
general household Inventory tool, not a reuse of it — mixing "kitchen
supplies" and "resistor stock" into one list would serve neither well,
and electronics parts want their own fields (value, package) that a
generic inventory item doesn't.
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
_COMPONENTS_FILE = _DATA_DIR / "components.json"
# Multi-user pass (2026-09-14) — the "shared object + user relationship"
# pattern's third real application (see core.kitchen_manager.
# RecipeUserStats' own docstring for the first, Recipes, and
# core.inventory_manager.InventoryUsageEntry's for the second,
# Inventory). Component itself stays shared/household; this file holds
# one real per-adjustment event, same shape as InventoryUsageEntry.
_USAGE_LOG_FILE = _DATA_DIR / "component_usage_log.json"


@dataclass
class Component:
    component_id: str
    name: str
    category: str = ""  # e.g. "Resistor", "Capacitor", "IC"
    value: str = ""  # e.g. "10k", "100nF"
    package: str = ""  # e.g. "THT", "0805"
    quantity: int = 0
    location: str = ""
    notes: str = ""
    updated_at: str = ""  # ISO datetime
    # Multi-user pass (2026-09-14) — who first added this component,
    # same role core.inventory_manager.InventoryItem.added_by_profile_id
    # plays. None (every component added before this field existed, or
    # with no active profile) means "unattributed," a real, valid state.
    added_by_profile_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "component_id": self.component_id,
            "name": self.name,
            "category": self.category,
            "value": self.value,
            "package": self.package,
            "quantity": self.quantity,
            "location": self.location,
            "notes": self.notes,
            "updated_at": self.updated_at,
            "added_by_profile_id": self.added_by_profile_id,
        }

    @staticmethod
    def from_dict(data: dict) -> "Component":
        return Component(
            component_id=data.get("component_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            category=data.get("category", ""),
            value=data.get("value", ""),
            package=data.get("package", ""),
            quantity=data.get("quantity", 0),
            location=data.get("location", ""),
            notes=data.get("notes", ""),
            updated_at=data.get("updated_at", ""),
            added_by_profile_id=data.get("added_by_profile_id"),
        )


@dataclass
class ComponentUsageEntry:
    """One real quantity adjustment, attributed to whoever was active
    when it happened — same shape and role as
    core.inventory_manager.InventoryUsageEntry. `delta` is negative for
    real consumption (pulled a resistor for a build) and positive for
    a restock; `times_used()`/`last_used()` below only count the
    negative ones."""

    entry_id: str
    component_id: str
    delta: int
    profile_id: Optional[str] = None
    timestamp: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "component_id": self.component_id,
            "delta": self.delta,
            "profile_id": self.profile_id,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_dict(data: dict) -> "ComponentUsageEntry":
        return ComponentUsageEntry(
            entry_id=data.get("entry_id", uuid.uuid4().hex[:10]),
            component_id=data.get("component_id", ""),
            delta=data.get("delta", 0),
            profile_id=data.get("profile_id"),
            timestamp=data.get("timestamp", ""),
        )


class ComponentManager:
    def __init__(self, context: AppContext, data_dir: Optional[Path] = None) -> None:
        # Whose data: a household's own folder (core/personal_data.py), or data/ by default.
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._components_file = self.data_dir / "components.json" if data_dir is not None else _COMPONENTS_FILE
        self._usage_log_file = self.data_dir / "component_usage_log.json" if data_dir is not None else _USAGE_LOG_FILE
        self.context = context
        self._components: list[Component] = []
        self._usage_log: list[ComponentUsageEntry] = []
        self._load()
        self._load_usage_log()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._components_file.exists():
            self._components = []
            return
        try:
            raw = json.loads(self._components_file.read_text(encoding="utf-8"))
            self._components = [Component.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load components.json — starting with an empty list.")
            notify_data_corruption(self.context, "components.json")
            self._components = []

    def _load_usage_log(self) -> None:
        if not self._usage_log_file.exists():
            self._usage_log = []
            return
        try:
            raw = json.loads(self._usage_log_file.read_text(encoding="utf-8"))
            self._usage_log = [ComponentUsageEntry.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load component_usage_log.json — starting with an empty list.")
            notify_data_corruption(self.context, "component_usage_log.json")
            self._usage_log = []

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._components_file,
            json.dumps([c.to_dict() for c in self._components], indent=2),
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

    def add_component(
        self,
        name: str,
        category: str = "",
        value: str = "",
        package: str = "",
        quantity: int = 0,
        location: str = "",
        notes: str = "",
    ) -> Component:
        component = Component(
            component_id=uuid.uuid4().hex[:10],
            name=name,
            category=category,
            value=value,
            package=package,
            quantity=max(0, quantity),
            location=location,
            notes=notes,
            updated_at=datetime.now().isoformat(timespec="seconds"),
            added_by_profile_id=self._active_profile_id(),
        )
        self._components.append(component)
        self._save()
        log.info("Component added: '%s' (qty %d)", name, component.quantity)
        return component

    def adjust_quantity(self, component_id: str, delta: int) -> Component:
        """Quick +1/-1 adjust — clamps at 0 rather than going negative.
        Multi-user pass (2026-09-14) — same shape as
        core.inventory_manager.InventoryManager.adjust_quantity(): a
        real, non-zero delta also appends a ComponentUsageEntry
        attributed to whoever's active. A clamped-to-0 delta still logs
        the attempt as a real event, same reasoning as Inventory's own
        adjust_quantity() docstring."""
        component = self.get_component(component_id)
        if component is None:
            raise ValueError(f"No component with id '{component_id}'.")
        component.quantity = max(0, component.quantity + delta)
        component.updated_at = datetime.now().isoformat(timespec="seconds")
        if delta != 0:
            self._usage_log.append(ComponentUsageEntry(
                entry_id=uuid.uuid4().hex[:10],
                component_id=component_id,
                delta=delta,
                profile_id=self._active_profile_id(),
                timestamp=component.updated_at,
            ))
            self._save_usage_log()
        self._save()
        return component

    def update_component(self, component_id: str, **fields) -> Component:
        component = self.get_component(component_id)
        if component is None:
            raise ValueError(f"No component with id '{component_id}'.")
        for key, value in fields.items():
            if key == "updated_at":
                raise ValueError("'updated_at' can't be set through update_component().")
            if not hasattr(component, key):
                raise ValueError(f"Component has no field '{key}'.")
            setattr(component, key, value)
        if component.quantity < 0:
            component.quantity = 0
        component.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return component

    def delete_component(self, component_id: str) -> None:
        self._components = [c for c in self._components if c.component_id != component_id]
        self._save()

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_component(self, component_id: str) -> Optional[Component]:
        for component in self._components:
            if component.component_id == component_id:
                return component
        return None

    def all_components(self) -> list[Component]:
        return sorted(self._components, key=lambda c: c.name.lower())

    def search(self, query: str) -> list[Component]:
        """Case-insensitive substring match over name, category, value, package, location, and notes."""
        query_lower = query.strip().lower()
        if not query_lower:
            return []

        matches = []
        for component in self._components:
            haystack = (
                f"{component.name} {component.category} {component.value} "
                f"{component.package} {component.location} {component.notes}"
            ).lower()
            if query_lower in haystack:
                matches.append(component)
        return sorted(matches, key=lambda c: c.name.lower())

    # ------------------------------------------------------------------
    # Usage (multi-user pass, 2026-09-14) — see ComponentUsageEntry's
    # own docstring; direct analog of
    # core.inventory_manager.InventoryManager's usage_log_for_item()/
    # times_used()/last_used().
    # ------------------------------------------------------------------

    def usage_log_for_component(self, component_id: str) -> list[ComponentUsageEntry]:
        """Every real adjustment (both restocks and consumption) for this component, oldest first."""
        return [e for e in self._usage_log if e.component_id == component_id]

    def times_used(self, component_id: str, profile_id: Optional[str] = None) -> int:
        """Real consumption events only (delta < 0). `profile_id=None`
        (the default) is the real household total; a real profile_id
        counts only entries attributed to that profile OR unattributed
        — same semantics core.inventory_manager's own times_used()
        already established for the identical question."""
        return sum(
            1 for e in self._usage_log
            if e.component_id == component_id and e.delta < 0
            and (profile_id is None or e.profile_id is None or e.profile_id == profile_id)
        )

    def last_used(self, component_id: str, profile_id: Optional[str] = None) -> Optional[ComponentUsageEntry]:
        """Same `profile_id` semantics as times_used() above. Picks the
        last MATCHING entry by real append order, not by comparing
        `timestamp` strings — core.inventory_manager.InventoryManager.
        last_used()'s own docstring explains why (several quick
        adjustments can share a one-second-resolution timestamp)."""
        matches = [
            e for e in self._usage_log
            if e.component_id == component_id and e.delta < 0
            and (profile_id is None or e.profile_id is None or e.profile_id == profile_id)
        ]
        if not matches:
            return None
        return matches[-1]
