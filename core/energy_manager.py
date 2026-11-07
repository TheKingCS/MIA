"""
core.energy_manager
======================

Manual energy/utility source tracking — 2026-09-09, the last of four
"Field Manual" brainstorm items the user picked this session. Original
seed: "Solar, generator, propane are currently just Maintenance usage
logs by convention — could be a real Power/Energy expansion once real
monitoring hardware exists." Asked the user directly whether real
hardware exists to integrate; they confirmed "Manual entry for now" —
no hardware backend here, `log_energy_reading()` is the only write
path, same "just another caller of add_reading(), not a different
backend to plug in here" framing core.data_logger_manager's own
docstring already uses for future hardware.

Deliberately a new sibling manager, NOT bolted onto core/power_manager
.py: that module's PowerStatus/PowerBackend model one instantaneous
device-battery reading, a fundamentally different shape than multiple
named sources each with their own historical time-series readings.
EnergyManager reads context.data_logger the same way
core.real_estate_manager.RealEstateManager reads context.budget — a
new domain, not a second concern merged into an existing narrow-purpose
manager's file. Every manager in this project lives one-per-file; this
follows that convention rather than being an exception to it.

log_energy_reading()/energy_source_meter_names()/energy_source_readings()
are an exact mirror of core.maintenance_manager.MaintenanceManager's
own log_asset_reading()/asset_meter_names()/asset_readings() — the
proven shape for "a named thing with an arbitrary set of named
meters/readings, scoped through one shared DataLoggerManager, zero
separate reading storage of its own." A series exists implicitly the
moment it has a reading, same convention DataLoggerManager itself
uses — energy_source_meter_names() derives the known set by filtering
context.data_logger.list_series() for this source's series-id prefix,
never a separately stored list.

delete_energy_source() removes the EnergySource record only — its
DataLogger readings are left in place, unreachable through this
manager's own API once get_energy_source() returns None, but never
physically deleted, same "deleting a parent doesn't delete real
history" stance core.real_estate_manager.RealEstateManager
.delete_property() and core.budget_manager.BudgetManager
.delete_business_entity() already take. energy_source_meter_names()/
energy_source_readings() don't gate on the source still existing
either, matching the mirrored asset methods exactly.
"""

from __future__ import annotations

from core import life_events

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.data_logger_manager import Reading
from core.logger import get_logger
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_ENERGY_SOURCES_FILE = _DATA_DIR / "energy_sources.json"

ENERGY_SOURCE_TYPES = ["Solar", "Generator", "Propane", "Battery Bank", "Other"]


@dataclass
class EnergySource:
    """A power or utility source the person tracks by hand (solar, a generator, propane...): its name, type
    (ENERGY_SOURCE_TYPES) and notes.
    """
    source_id: str
    name: str  # "Rooftop Solar Array", "Backup Generator" — arbitrary, user-defined
    source_type: str = "Other"  # one of ENERGY_SOURCE_TYPES
    notes: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        """The record as the plain dict saved in its JSON file."""
        return {
            "source_id": self.source_id, "name": self.name, "source_type": self.source_type,
            "notes": self.notes, "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "EnergySource":
        """A record from its saved dict; a missing field takes its default, so older files load."""
        return EnergySource(
            source_id=data.get("source_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            source_type=data.get("source_type", "Other"),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
        )


class EnergyManager:
    """The household's energy sources (energy_sources.json, written through atomic_write_text); their readings live in
    the Data Logger, one series per source and meter, so a sensor later is just another writer.
    """
    def __init__(self, context: AppContext, data_dir: Optional[Path] = None) -> None:
        # Whose data: a household's own folder (core/personal_data.py), or data/ by default.
        """Points at its file (data/ by default) and loads it."""
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._energy_sources_file = self.data_dir / "energy_sources.json" if data_dir is not None else _ENERGY_SOURCES_FILE
        self.context = context
        self._sources: list[EnergySource] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Reads the sources; a damaged file is logged, reported and starts empty."""
        if not self._energy_sources_file.exists():
            self._sources = []
            return
        try:
            raw = json.loads(self._energy_sources_file.read_text(encoding="utf-8"))
            self._sources = [EnergySource.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load energy_sources.json — starting with an empty list.")
            notify_data_corruption(self.context, "energy_sources.json")
            self._sources = []

    def _save(self) -> None:
        """Writes the sources atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._energy_sources_file,
            json.dumps([s.to_dict() for s in self._sources], indent=2), encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Energy source CRUD
    # ------------------------------------------------------------------

    @life_events.on_change("energy_source_added", "an energy source", "energy_source")
    def add_energy_source(self, name: str, source_type: str = "Other", notes: str = "") -> EnergySource:
        """Adds a source (an unknown type becomes Other)."""
        source = EnergySource(
            source_id=uuid.uuid4().hex[:10],
            name=name,
            source_type=source_type if source_type in ENERGY_SOURCE_TYPES else "Other",
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._sources.append(source)
        self._save()
        log.info("Energy source added: '%s' (%s)", source.name, source.source_type)
        return source

    @life_events.on_change("energy_source_updated", "an energy source", "energy_source")
    def update_energy_source(self, source_id: str, **fields) -> EnergySource:
        """Changes a source's fields (an unknown type becomes Other; ValueError for an unknown source or field)."""
        source = self.get_energy_source(source_id)
        if source is None:
            raise ValueError(f"No energy source with id '{source_id}'.")
        for key, value in fields.items():
            if not hasattr(source, key):
                raise ValueError(f"EnergySource has no field '{key}'.")
            setattr(source, key, value)
        if source.source_type not in ENERGY_SOURCE_TYPES:
            source.source_type = "Other"
        self._save()
        return source

    @life_events.on_change("energy_source_removed", "an energy source", "energy_source")
    def delete_energy_source(self, source_id: str) -> None:
        """Deletes the EnergySource record only — see module docstring
        for why its logged readings are deliberately left in place."""
        self._sources = [s for s in self._sources if s.source_id != source_id]
        self._save()

    def get_energy_source(self, source_id: str) -> Optional[EnergySource]:
        """The source with this id, or None."""
        for source in self._sources:
            if source.source_id == source_id:
                return source
        return None

    def all_energy_sources(self) -> list[EnergySource]:
        """Every source, by name."""
        return sorted(self._sources, key=lambda s: s.name.lower())

    # ------------------------------------------------------------------
    # Readings — thin passthrough to the shared DataLoggerManager,
    # exact mirror of MaintenanceManager's asset-reading methods
    # ------------------------------------------------------------------

    @staticmethod
    def _energy_source_series_id(source_id: str, meter_name: str) -> str:
        """The Data Logger series for one of a source's meters."""
        return f"energy_source_{source_id}_{meter_name}"

    @life_events.on_change("energy_reading_logged", "an energy reading", "energy_source")
    def log_energy_reading(self, source_id: str, meter_name: str, value: float, unit: str = "", note: str = "") -> Reading:
        """Logs a reading on one of a source's meters ("kWh produced", "tank %")."""
        if self.get_energy_source(source_id) is None:
            raise ValueError(f"No energy source with id '{source_id}'.")
        return self.context.data_logger.add_reading(
            series_id=self._energy_source_series_id(source_id, meter_name), value=value, unit=unit, note=note,
        )

    def energy_source_meter_names(self, source_id: str) -> list[str]:
        """Every meter name this source has at least one logged reading
        under, derived from Data Logger series ids rather than stored
        separately — same "a series exists implicitly the moment it has
        a reading" convention DataLoggerManager itself uses."""
        prefix = self._energy_source_series_id(source_id, "")
        return sorted(
            series_id[len(prefix):] for series_id in self.context.data_logger.list_series()
            if series_id.startswith(prefix)
        )

    def energy_source_readings(self, source_id: str, meter_name: str) -> list[Reading]:
        """The readings on one of a source's meters."""
        return self.context.data_logger.readings_for(self._energy_source_series_id(source_id, meter_name))
