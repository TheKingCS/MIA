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

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_COMPONENTS_FILE = _DATA_DIR / "components.json"


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
        )


class ComponentManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._components: list[Component] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _COMPONENTS_FILE.exists():
            self._components = []
            return
        try:
            raw = json.loads(_COMPONENTS_FILE.read_text(encoding="utf-8"))
            self._components = [Component.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load components.json — starting with an empty list.")
            self._components = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_COMPONENTS_FILE,
            json.dumps([c.to_dict() for c in self._components], indent=2),
            encoding="utf-8",
        )

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
        )
        self._components.append(component)
        self._save()
        log.info("Component added: '%s' (qty %d)", name, component.quantity)
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
