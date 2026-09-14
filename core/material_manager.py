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

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_MATERIALS_FILE = _DATA_DIR / "materials.json"


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
        )


def materials_needing_restock(materials: list[Material]) -> list[Material]:
    """Pure logic — testable without I/O. See this module's docstring
    for why this replaces the proposed schema's SQL view."""
    return [m for m in materials if m.quantity_on_hand <= m.reorder_threshold]


class MaterialManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._materials: list[Material] = []
        self._load()

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
            self._materials = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_MATERIALS_FILE,
            json.dumps([m.to_dict() for m in self._materials], indent=2),
            encoding="utf-8",
        )

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
        )
        self._materials.append(material)
        self._save()
        log.info("Material added: '%s' (qty %s %s)", name, material.quantity_on_hand, material.unit)
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
