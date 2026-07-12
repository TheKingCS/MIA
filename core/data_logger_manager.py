"""
core.data_logger_manager
==========================

The Data Logger + Charts shared service — docs/ROADMAP.md milestone
8.1, the "Data Logger + Charts" row of the shared core services table
(used by Multimeter logging, soil moisture, power usage, Lab
experiments/calibration, sensor testing, vehicle diagnostics).

Same persisted-JSON pattern as core/inventory_manager.py:
data/data_logger_readings.json, a dataclass with to_dict/from_dict, a
manager class wrapping load/save. Readings are grouped by an arbitrary
`series_id` string (e.g. "multimeter_voltage", "soil_moisture") that's
created implicitly the first time a reading is added to it — no
separate series-registry file, since a series is just "whatever
distinct series_id strings currently have readings," not something
that needs to exist before its first reading.

No hardware-specific reading producer exists yet — every current
caller (modules/lab/module.py, milestone 8.2) is a manual entry form.
A future real-sensor/multimeter integration is just another caller of
add_reading(), not a different backend to plug in here.
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

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_READINGS_FILE = _DATA_DIR / "data_logger_readings.json"


@dataclass
class Reading:
    reading_id: str
    series_id: str
    value: float
    unit: str = ""
    note: str = ""
    timestamp: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "reading_id": self.reading_id,
            "series_id": self.series_id,
            "value": self.value,
            "unit": self.unit,
            "note": self.note,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_dict(data: dict) -> "Reading":
        return Reading(
            reading_id=data.get("reading_id", uuid.uuid4().hex[:10]),
            series_id=data.get("series_id", ""),
            value=data.get("value", 0.0),
            unit=data.get("unit", ""),
            note=data.get("note", ""),
            timestamp=data.get("timestamp", ""),
        )


class DataLoggerManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._readings: list[Reading] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _READINGS_FILE.exists():
            self._readings = []
            return
        try:
            raw = json.loads(_READINGS_FILE.read_text(encoding="utf-8"))
            self._readings = [Reading.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load data_logger_readings.json — starting with an empty list.")
            self._readings = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _READINGS_FILE.write_text(
            json.dumps([r.to_dict() for r in self._readings], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def add_reading(
        self,
        series_id: str,
        value: float,
        unit: str = "",
        note: str = "",
        timestamp: Optional[str] = None,
    ) -> Reading:
        reading = Reading(
            reading_id=uuid.uuid4().hex[:10],
            series_id=series_id,
            value=value,
            unit=unit,
            note=note,
            timestamp=timestamp or datetime.now().isoformat(timespec="seconds"),
        )
        self._readings.append(reading)
        self._save()
        log.info("Data Logger reading added to series '%s': %s %s", series_id, value, unit)
        return reading

    def delete_reading(self, reading_id: str) -> None:
        self._readings = [r for r in self._readings if r.reading_id != reading_id]
        self._save()

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def list_series(self) -> list[str]:
        """Every distinct series_id that currently has at least one reading, alphabetically."""
        return sorted({r.series_id for r in self._readings})

    def readings_for(self, series_id: str) -> list[Reading]:
        """All readings in `series_id`, oldest first (chart/table display order)."""
        matches = [r for r in self._readings if r.series_id == series_id]
        return sorted(matches, key=lambda r: r.timestamp)
