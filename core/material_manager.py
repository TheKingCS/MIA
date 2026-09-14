"""
core.material_manager
========================

MIA Home's fabrication-materials inventory — the first concrete slice
of the proposed `mia_home_schema.sql`'s `materials` table (see
`docs/VISION.md`'s "MIA Home's expanded scope" section), adapted to
this project's persisted-JSON-manager convention rather than adopting
SQLite, per the user's explicit call. Same persisted-JSON pattern as
`core/component_manager.py`: `data/materials.json`, a dataclass with
`to_dict`/`from_dict`, a manager class wrapping load/save.

Deliberately a *third* separate manager/dataset, not a reuse of
`core/inventory_manager.py` (general household Inventory) or
`core/component_manager.py` (electronics Component DB) — same reasoning
that Component DB's own docstring already gives for being separate
from Inventory: mixing "kitchen supplies," "resistor stock," and
"plywood/filament stock costed for a fab job" into one list would serve
none of them well, and fabrication materials want their own fields
(`unit_cost`, `reorder_threshold`) neither of the other two has.

`jobs`/`products`/`product_listings`/`revenue`/`expenses` and
`material_consumption` (the rest of the proposed schema) are
deliberately NOT built in this pass — scoped down to just this
foundational piece first, at the user's explicit call, same "one
slice at a time" discipline as every other MIA Home addition this
session. `cost_rates`/`labor_rate` (simple scalar settings, not
many-record entities) will likely become plain config keys
(`workshop.*`) rather than their own managers when jobs are built,
matching this project's existing config-vs-manager distinction — not
decided yet, flagged here for whenever that slice happens.

`materials_needing_restock()` is a plain Python function over
already-loaded records — the same "compute on demand so it can never
go stale" precedent `core/memory_manager.py` already established for
its own `ExpeditionRecap` aggregation — rather than the proposed
schema's SQL view, which has no direct equivalent once there's no
database underneath it.
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
_MATERIALS_FILE = _DATA_DIR / "materials.json"
# Multi-user pass (2026-09-14) — the "shared object + user relationship"
# pattern's fourth real application (see core.component_manager.
# ComponentUsageEntry's own docstring for the third, Component DB, and
# core.inventory_manager's for the second, Inventory). Material itself
# stays shared/household; this file holds one real per-adjustment
# event, same shape as ComponentUsageEntry/InventoryUsageEntry — with
# a `float` delta rather than `int`, matching this domain's own
# continuous units (kg, sheets, ft) that the other two don't have.
_USAGE_LOG_FILE = _DATA_DIR / "material_usage_log.json"


@dataclass
class Material:
    material_id: str
    name: str
    unit: str = ""  # e.g. "sheet", "kg", "spool", "ft"
    unit_cost: float = 0.0  # cost per unit, for future job/product costing
    quantity_on_hand: float = 0.0
    reorder_threshold: float = 0.0  # materials_needing_restock() flags quantity_on_hand <= this
    supplier: str = ""
    location: str = ""
    notes: str = ""
    updated_at: str = ""  # ISO datetime
    # Multi-user pass (2026-09-14) — who first added this material,
    # same role core.component_manager.Component.added_by_profile_id/
    # core.inventory_manager.InventoryItem.added_by_profile_id play.
    added_by_profile_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "material_id": self.material_id,
            "name": self.name,
            "unit": self.unit,
            "unit_cost": self.unit_cost,
            "quantity_on_hand": self.quantity_on_hand,
            "reorder_threshold": self.reorder_threshold,
            "supplier": self.supplier,
            "location": self.location,
            "notes": self.notes,
            "updated_at": self.updated_at,
            "added_by_profile_id": self.added_by_profile_id,
        }

    @staticmethod
    def from_dict(data: dict) -> "Material":
        return Material(
            material_id=data.get("material_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            unit=data.get("unit", ""),
            unit_cost=data.get("unit_cost", 0.0),
            quantity_on_hand=data.get("quantity_on_hand", 0.0),
            reorder_threshold=data.get("reorder_threshold", 0.0),
            supplier=data.get("supplier", ""),
            location=data.get("location", ""),
            notes=data.get("notes", ""),
            updated_at=data.get("updated_at", ""),
            added_by_profile_id=data.get("added_by_profile_id"),
        )


@dataclass
class MaterialUsageEntry:
    """One real quantity adjustment, attributed to whoever was active
    when it happened — same shape and role as
    core.component_manager.ComponentUsageEntry, except `delta` is a
    `float` (materials use continuous units like kg/sheets/ft, unlike
    Inventory/Components' discrete counts). Populated by both real
    sources of a material's quantity changing: a direct manual
    adjustment, and core.job_manager.JobManager.consume_material() (a
    real Job consuming stock) — see MaterialManager.adjust_quantity()'s
    own docstring for why both flow through the same method."""

    entry_id: str
    material_id: str
    delta: float
    profile_id: Optional[str] = None
    timestamp: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "material_id": self.material_id,
            "delta": self.delta,
            "profile_id": self.profile_id,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_dict(data: dict) -> "MaterialUsageEntry":
        return MaterialUsageEntry(
            entry_id=data.get("entry_id", uuid.uuid4().hex[:10]),
            material_id=data.get("material_id", ""),
            delta=data.get("delta", 0.0),
            profile_id=data.get("profile_id"),
            timestamp=data.get("timestamp", ""),
        )


def materials_needing_restock(materials: list[Material]) -> list[Material]:
    """Pure logic — testable without I/O. See this module's docstring
    for why this replaces the proposed schema's SQL view."""
    return [m for m in materials if m.quantity_on_hand <= m.reorder_threshold]


class MaterialManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._materials: list[Material] = []
        self._usage_log: list[MaterialUsageEntry] = []
        self._load()
        self._load_usage_log()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _MATERIALS_FILE.exists():
            self._materials = []
            return
        try:
            raw = json.loads(_MATERIALS_FILE.read_text(encoding="utf-8"))
            self._materials = [Material.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load materials.json — starting with an empty list.")
            notify_data_corruption(self.context, "materials.json")
            self._materials = []

    def _load_usage_log(self) -> None:
        if not _USAGE_LOG_FILE.exists():
            self._usage_log = []
            return
        try:
            raw = json.loads(_USAGE_LOG_FILE.read_text(encoding="utf-8"))
            self._usage_log = [MaterialUsageEntry.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load material_usage_log.json — starting with an empty list.")
            notify_data_corruption(self.context, "material_usage_log.json")
            self._usage_log = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_MATERIALS_FILE,
            json.dumps([m.to_dict() for m in self._materials], indent=2),
            encoding="utf-8",
        )

    def _save_usage_log(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(
            _USAGE_LOG_FILE,
            json.dumps([e.to_dict() for e in self._usage_log], indent=2),
            encoding="utf-8",
        )

    def _active_profile_id(self) -> Optional[str]:
        active_profile = self.context.profiles.get_active_profile() if self.context.profiles is not None else None
        return active_profile.profile_id if active_profile is not None else None

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def add_material(
        self,
        name: str,
        unit: str = "",
        unit_cost: float = 0.0,
        quantity_on_hand: float = 0.0,
        reorder_threshold: float = 0.0,
        supplier: str = "",
        location: str = "",
        notes: str = "",
    ) -> Material:
        material = Material(
            material_id=uuid.uuid4().hex[:10],
            name=name,
            unit=unit,
            unit_cost=max(0.0, unit_cost),
            quantity_on_hand=max(0.0, quantity_on_hand),
            reorder_threshold=max(0.0, reorder_threshold),
            supplier=supplier,
            location=location,
            notes=notes,
            updated_at=datetime.now().isoformat(timespec="seconds"),
            added_by_profile_id=self._active_profile_id(),
        )
        self._materials.append(material)
        self._save()
        log.info("Material added: '%s' (qty %s %s)", name, material.quantity_on_hand, material.unit)
        return material

    def adjust_quantity(self, material_id: str, delta: float) -> Material:
        """Quick adjust — clamps at 0 rather than going negative. Multi-
        user pass (2026-09-14) — a real, non-zero delta also appends a
        MaterialUsageEntry attributed to whoever's active, same shape as
        core.component_manager.ComponentManager.adjust_quantity() and
        core.inventory_manager.InventoryManager.adjust_quantity().
        core.job_manager.JobManager.consume_material() calls this too
        (with a negative delta) rather than update_material() directly,
        so a real Job consuming stock is also real, attributed usage —
        not just a manual quantity tweak counts."""
        material = self.get_material(material_id)
        if material is None:
            raise ValueError(f"No material with id '{material_id}'.")
        material.quantity_on_hand = max(0.0, material.quantity_on_hand + delta)
        material.updated_at = datetime.now().isoformat(timespec="seconds")
        if delta != 0:
            self._usage_log.append(MaterialUsageEntry(
                entry_id=uuid.uuid4().hex[:10],
                material_id=material_id,
                delta=delta,
                profile_id=self._active_profile_id(),
                timestamp=material.updated_at,
            ))
            self._save_usage_log()
        self._save()
        return material

    def update_material(self, material_id: str, **fields) -> Material:
        material = self.get_material(material_id)
        if material is None:
            raise ValueError(f"No material with id '{material_id}'.")
        for key, value in fields.items():
            if key == "updated_at":
                raise ValueError("'updated_at' can't be set through update_material().")
            if not hasattr(material, key):
                raise ValueError(f"Material has no field '{key}'.")
            setattr(material, key, value)
        if material.quantity_on_hand < 0:
            material.quantity_on_hand = 0
        if material.unit_cost < 0:
            material.unit_cost = 0
        if material.reorder_threshold < 0:
            material.reorder_threshold = 0
        material.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return material

    def delete_material(self, material_id: str) -> None:
        self._materials = [m for m in self._materials if m.material_id != material_id]
        self._save()

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_material(self, material_id: str) -> Optional[Material]:
        for material in self._materials:
            if material.material_id == material_id:
                return material
        return None

    def all_materials(self) -> list[Material]:
        return sorted(self._materials, key=lambda m: m.name.lower())

    def search(self, query: str) -> list[Material]:
        """Case-insensitive substring match over name, supplier, location, and notes."""
        query_lower = query.strip().lower()
        if not query_lower:
            return []

        matches = []
        for material in self._materials:
            haystack = f"{material.name} {material.supplier} {material.location} {material.notes}".lower()
            if query_lower in haystack:
                matches.append(material)
        return sorted(matches, key=lambda m: m.name.lower())

    def materials_needing_restock(self) -> list[Material]:
        return materials_needing_restock(self._materials)

    # ------------------------------------------------------------------
    # Usage (multi-user pass, 2026-09-14) — see MaterialUsageEntry's own
    # docstring; direct analog of core.component_manager.ComponentManager's
    # usage_log_for_component()/times_used()/last_used().
    # ------------------------------------------------------------------

    def usage_log_for_material(self, material_id: str) -> list[MaterialUsageEntry]:
        """Every real adjustment (both restocks and consumption) for this material, oldest first."""
        return [e for e in self._usage_log if e.material_id == material_id]

    def times_used(self, material_id: str, profile_id: Optional[str] = None) -> int:
        """Real consumption events only (delta < 0) — includes both
        manual adjustments and real Job consumption (see
        adjust_quantity()'s own docstring). `profile_id=None` (the
        default) is the real household total; a real profile_id counts
        only entries attributed to that profile OR unattributed — same
        semantics core.component_manager/core.inventory_manager already
        established for the identical question."""
        return sum(
            1 for e in self._usage_log
            if e.material_id == material_id and e.delta < 0
            and (profile_id is None or e.profile_id is None or e.profile_id == profile_id)
        )

    def last_used(self, material_id: str, profile_id: Optional[str] = None) -> Optional[MaterialUsageEntry]:
        """Same `profile_id` semantics as times_used() above. Picks the
        last MATCHING entry by real append order, not by comparing
        `timestamp` strings — see
        core.inventory_manager.InventoryManager.last_used()'s own
        docstring for why."""
        matches = [
            e for e in self._usage_log
            if e.material_id == material_id and e.delta < 0
            and (profile_id is None or e.profile_id is None or e.profile_id == profile_id)
        ]
        if not matches:
            return None
        return matches[-1]
