"""
core.waypoint_manager
========================

Backs the Navigation module's waypoint list (modules/navigation/module.py)
— docs/ROADMAP.md milestone 10.1. Same persisted-JSON pattern as
core/inventory_manager.py: data/waypoints.json, a dataclass with
to_dict/from_dict, a manager class wrapping load/save.

haversine_distance_km()/initial_bearing_degrees() are free functions
(pure math, no dependency on this class or any hardware) so they're
unit-testable against known real-world distances/bearings — see
tests/test_waypoint_manager.py. Genuinely useful even without real GPS
hardware: coordinates can be entered by hand from a paper map or
another GPS device, and distance/bearing between two known points is
exactly what a compass-and-map user needs.
"""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_WAYPOINTS_FILE = _DATA_DIR / "waypoints.json"

_EARTH_RADIUS_KM = 6371.0088


@dataclass
class Waypoint:
    waypoint_id: str
    name: str
    latitude: float
    longitude: float
    notes: str = ""
    created_at: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "waypoint_id": self.waypoint_id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Waypoint":
        return Waypoint(
            waypoint_id=data.get("waypoint_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            latitude=data.get("latitude", 0.0),
            longitude=data.get("longitude", 0.0),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
        )


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometers."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _EARTH_RADIUS_KM * c


def initial_bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial compass bearing (0-360, 0 = north) from point 1 to point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    x = math.sin(delta_lambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


class WaypointManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._waypoints: list[Waypoint] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _WAYPOINTS_FILE.exists():
            self._waypoints = []
            return
        try:
            raw = json.loads(_WAYPOINTS_FILE.read_text(encoding="utf-8"))
            self._waypoints = [Waypoint.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load waypoints.json — starting with an empty list.")
            self._waypoints = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _WAYPOINTS_FILE.write_text(
            json.dumps([w.to_dict() for w in self._waypoints], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def add_waypoint(self, name: str, latitude: float, longitude: float, notes: str = "") -> Waypoint:
        waypoint = Waypoint(
            waypoint_id=uuid.uuid4().hex[:10],
            name=name,
            latitude=latitude,
            longitude=longitude,
            notes=notes,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._waypoints.append(waypoint)
        self._save()
        log.info("Waypoint added: '%s' (%s, %s)", name, latitude, longitude)
        return waypoint

    def update_waypoint(self, waypoint_id: str, **fields) -> Waypoint:
        waypoint = self.get_waypoint(waypoint_id)
        if waypoint is None:
            raise ValueError(f"No waypoint with id '{waypoint_id}'.")
        for key, value in fields.items():
            if key == "created_at":
                raise ValueError("'created_at' can't be set through update_waypoint().")
            if not hasattr(waypoint, key):
                raise ValueError(f"Waypoint has no field '{key}'.")
            setattr(waypoint, key, value)
        self._save()
        return waypoint

    def delete_waypoint(self, waypoint_id: str) -> None:
        self._waypoints = [w for w in self._waypoints if w.waypoint_id != waypoint_id]
        self._save()

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_waypoint(self, waypoint_id: str) -> Optional[Waypoint]:
        for waypoint in self._waypoints:
            if waypoint.waypoint_id == waypoint_id:
                return waypoint
        return None

    def all_waypoints(self) -> list[Waypoint]:
        return sorted(self._waypoints, key=lambda w: w.name.lower())

    def distance_and_bearing(self, from_id: str, to_id: str) -> Optional[tuple[float, float]]:
        """(distance_km, initial_bearing_degrees) from one waypoint to another, or None if either id is unknown."""
        origin = self.get_waypoint(from_id)
        destination = self.get_waypoint(to_id)
        if origin is None or destination is None:
            return None
        distance = haversine_distance_km(origin.latitude, origin.longitude, destination.latitude, destination.longitude)
        bearing = initial_bearing_degrees(origin.latitude, origin.longitude, destination.latitude, destination.longitude)
        return distance, bearing
