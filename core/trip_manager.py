"""
core.trip_manager
====================

Backs the Expeditions module (modules/expeditions/module.py) —
docs/ROADMAP.md milestone 12.1, Expedition Mode. A Trip is one outing —
a hike, paddle, ride, fishing trip, etc. (see `ACTIVITY_TYPES`) —
always belonging to a core.expedition_manager.Expedition via the
required `expedition_id`. It ties together a planned route (existing
Waypoints, in order), a gear checklist, logged speed/distance
checkpoints, and photos. Same persisted-JSON pattern as
core/waypoint_manager.py: data/trips.json, a dataclass with
to_dict/from_dict, a manager class wrapping load/save.

`GearItem` and `Split` are nested dataclasses nested inside `Trip`'s own
JSON, not separate top-level records — they only ever make sense in the
context of one trip, same reasoning as why waypoints/inventory/journal
are each their own top-level file instead.

Only `add_trip`/`update_trip`/`delete_trip`/`get_trip`/`all_trips`/
`trips_for_expedition` plus the route helpers and
`planned_route_distance_km` land in 12.1. Gear (`add_gear_item`/
`toggle_gear_packed`/`remove_gear_item`), logged checkpoints
(`record_split`/`leg_summaries`/`total_distance_km`/
`average_speed_kmh`), and photos (`add_photo`/`remove_photo`) land in
their own later milestones (12.3/12.5/12.7) — the dataclass fields exist
from the start so the schema doesn't need a migration later, but their
manager methods don't exist yet.
"""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger
from core.waypoint_manager import haversine_distance_km
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_TRIPS_FILE = _DATA_DIR / "trips.json"

# Photos are real binary files, not JSON — kept out of data/ entirely
# (same reasoning as core/reference_library_manager.py's root_path: a
# multi-photo trip archive shouldn't get swept into core/backup_manager.py's
# data/ rglob alongside small config/JSON documents). Config-resolvable,
# same _resolve_*_root_path() pattern as ReferenceLibraryManager.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_PHOTO_ROOT = _PROJECT_ROOT / "trip_photos"

#: Suggested vocabulary for Trip.activity_type, surfaced as a QComboBox in
#: gui/add_edit_trip_dialog.py — docs/ROADMAP.md's Expedition Mode
#: generalization beyond hiking/camping. Stored as a plain str, not an
#: enum, same reasoning as core/waypoint_manager.py's WAYPOINT_CATEGORIES:
#: an unrecognized/blank value just means "unspecified", never an error.
ACTIVITY_TYPES: tuple[str, ...] = (
    "Hiking",
    "Camping",
    "Fishing",
    "Kayaking",
    "Biking",
    "Other",
)


@dataclass
class GearItem:
    label: str  # display text; if item_id is set, this is a snapshot of the Inventory item's name at add-time
    item_id: Optional[str] = None  # links to InventoryManager, or None for ad-hoc gear not tracked in Inventory
    packed: bool = False

    def to_dict(self) -> dict:
        return {"label": self.label, "item_id": self.item_id, "packed": self.packed}

    @staticmethod
    def from_dict(data: dict) -> "GearItem":
        return GearItem(
            label=data.get("label", ""),
            item_id=data.get("item_id"),
            packed=data.get("packed", False),
        )


@dataclass
class Split:
    waypoint_id: str
    logged_at: str  # ISO datetime — when the user tapped "arrived here"

    def to_dict(self) -> dict:
        return {"waypoint_id": self.waypoint_id, "logged_at": self.logged_at}

    @staticmethod
    def from_dict(data: dict) -> "Split":
        return Split(waypoint_id=data.get("waypoint_id", ""), logged_at=data.get("logged_at", ""))


@dataclass
class LegSummary:
    """Not persisted — derived on demand by TripManager.leg_summaries() from a trip's Splits."""

    from_waypoint_id: str
    to_waypoint_id: str
    distance_km: float
    elapsed_hours: float
    speed_kmh: Optional[float]  # None if elapsed_hours <= 0 (same-second or out-of-order splits)


@dataclass
class Trip:
    trip_id: str
    expedition_id: str
    name: str
    start_date: str = ""  # ISO date
    end_date: str = ""
    status: str = "planned"  # "planned" | "active" | "completed"
    activity_type: str = ""  # one of ACTIVITY_TYPES, or "" for unspecified
    waypoint_ids: list[str] = field(default_factory=list)  # ordered planned route
    splits: list[Split] = field(default_factory=list)  # actual logged checkpoints
    gear: list[GearItem] = field(default_factory=list)
    photo_filenames: list[str] = field(default_factory=list)
    notes: str = ""
    created_at: str = ""  # ISO datetime
    updated_at: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "trip_id": self.trip_id,
            "expedition_id": self.expedition_id,
            "name": self.name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "status": self.status,
            "activity_type": self.activity_type,
            "waypoint_ids": list(self.waypoint_ids),
            "splits": [s.to_dict() for s in self.splits],
            "gear": [g.to_dict() for g in self.gear],
            "photo_filenames": list(self.photo_filenames),
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Trip":
        return Trip(
            trip_id=data.get("trip_id", uuid.uuid4().hex[:10]),
            expedition_id=data.get("expedition_id", ""),
            name=data.get("name", ""),
            start_date=data.get("start_date", ""),
            end_date=data.get("end_date", ""),
            status=data.get("status", "planned"),
            activity_type=data.get("activity_type", ""),
            waypoint_ids=list(data.get("waypoint_ids", [])),
            splits=[Split.from_dict(d) for d in data.get("splits", [])],
            gear=[GearItem.from_dict(d) for d in data.get("gear", [])],
            photo_filenames=list(data.get("photo_filenames", [])),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class TripManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._trips: list[Trip] = []
        self._load()

        self._photo_root = self._resolve_photo_root_path()
        try:
            self._photo_root.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Same rationale as ReferenceLibraryManager: don't crash the
            # app over a missing/unmounted photo storage location —
            # photo actions below just log and no-op if this folder
            # isn't there when actually needed.
            log.warning("Could not create/access trip photo folder: %s", self._photo_root)

    def _resolve_photo_root_path(self) -> Path:
        configured = self.context.config.get("trips.photo_root_path", "")
        if configured:
            return Path(configured).expanduser()
        return _DEFAULT_PHOTO_ROOT

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _TRIPS_FILE.exists():
            self._trips = []
            return
        try:
            raw = json.loads(_TRIPS_FILE.read_text(encoding="utf-8"))
            self._trips = [Trip.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load trips.json — starting with an empty list.")
            notify_data_corruption(self.context, "trips.json")
            self._trips = []

    def reload(self) -> None:
        """Re-reads trips.json from disk — see ExpeditionManager.reload()'s docstring for why."""
        self._load()

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_TRIPS_FILE,
            json.dumps([t.to_dict() for t in self._trips], indent=2),
            encoding="utf-8",
        )

    def _bump_updated_at(self, trip: Trip) -> None:
        trip.updated_at = datetime.now().isoformat(timespec="seconds")

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def add_trip(
        self,
        expedition_id: str,
        name: str,
        start_date: str = "",
        end_date: str = "",
        activity_type: str = "",
        notes: str = "",
    ) -> Trip:
        now = datetime.now().isoformat(timespec="seconds")
        trip = Trip(
            trip_id=uuid.uuid4().hex[:10],
            expedition_id=expedition_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
            activity_type=activity_type,
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        self._trips.append(trip)
        self._save()
        log.info("Trip added: '%s' (expedition %s)", name, expedition_id)
        return trip

    def update_trip(self, trip_id: str, **fields) -> Trip:
        trip = self.get_trip(trip_id)
        if trip is None:
            raise ValueError(f"No trip with id '{trip_id}'.")
        for key, value in fields.items():
            if key in ("created_at", "expedition_id"):
                raise ValueError(f"'{key}' can't be set through update_trip().")
            if not hasattr(trip, key):
                raise ValueError(f"Trip has no field '{key}'.")
            setattr(trip, key, value)
        self._bump_updated_at(trip)
        self._save()
        return trip

    def delete_trip(self, trip_id: str) -> None:
        self._trips = [t for t in self._trips if t.trip_id != trip_id]
        self._save()

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_trip(self, trip_id: str) -> Optional[Trip]:
        for trip in self._trips:
            if trip.trip_id == trip_id:
                return trip
        return None

    def all_trips(self) -> list[Trip]:
        return sorted(self._trips, key=lambda t: t.start_date)

    def trips_for_expedition(self, expedition_id: str) -> list[Trip]:
        return sorted(
            (t for t in self._trips if t.expedition_id == expedition_id),
            key=lambda t: t.start_date,
        )

    # ------------------------------------------------------------------
    # Route (planned waypoint sequence)
    # ------------------------------------------------------------------

    def add_waypoint_to_route(self, trip_id: str, waypoint_id: str) -> Trip:
        trip = self.get_trip(trip_id)
        if trip is None:
            raise ValueError(f"No trip with id '{trip_id}'.")
        trip.waypoint_ids.append(waypoint_id)
        self._bump_updated_at(trip)
        self._save()
        return trip

    def remove_waypoint_from_route(self, trip_id: str, waypoint_id: str) -> Trip:
        trip = self.get_trip(trip_id)
        if trip is None:
            raise ValueError(f"No trip with id '{trip_id}'.")
        # Removes only the first occurrence — a route can legitimately
        # revisit the same waypoint (an out-and-back hike), so removing
        # every occurrence would be surprising.
        if waypoint_id in trip.waypoint_ids:
            trip.waypoint_ids.remove(waypoint_id)
        self._bump_updated_at(trip)
        self._save()
        return trip

    # ------------------------------------------------------------------
    # Gear checklist
    # ------------------------------------------------------------------

    def add_gear_item(self, trip_id: str, label: str, item_id: Optional[str] = None) -> Trip:
        trip = self.get_trip(trip_id)
        if trip is None:
            raise ValueError(f"No trip with id '{trip_id}'.")
        trip.gear.append(GearItem(label=label, item_id=item_id, packed=False))
        self._bump_updated_at(trip)
        self._save()
        return trip

    def toggle_gear_packed(self, trip_id: str, index: int) -> Trip:
        trip = self.get_trip(trip_id)
        if trip is None:
            raise ValueError(f"No trip with id '{trip_id}'.")
        if not (0 <= index < len(trip.gear)):
            raise ValueError(f"Trip '{trip_id}' has no gear item at index {index}.")
        trip.gear[index].packed = not trip.gear[index].packed
        self._bump_updated_at(trip)
        self._save()
        return trip

    def remove_gear_item(self, trip_id: str, index: int) -> Trip:
        trip = self.get_trip(trip_id)
        if trip is None:
            raise ValueError(f"No trip with id '{trip_id}'.")
        if not (0 <= index < len(trip.gear)):
            raise ValueError(f"Trip '{trip_id}' has no gear item at index {index}.")
        del trip.gear[index]
        self._bump_updated_at(trip)
        self._save()
        return trip

    def planned_route_distance_km(self, trip_id: str) -> Optional[float]:
        """
        Sum of haversine_distance_km() over the trip's planned route, in
        order. This is an upfront estimate from the route alone — it
        doesn't require the trip to have actually happened yet, unlike
        the logged-checkpoint distance below. Waypoints that no longer
        resolve (e.g. deleted from Navigation since being added to this
        route) are skipped rather than raising. Returns None if fewer
        than two waypoints in the route resolve.
        """
        trip = self.get_trip(trip_id)
        if trip is None:
            return None

        waypoints_manager = self.context.waypoints
        if waypoints_manager is None:
            return None

        total_km = 0.0
        resolved_count = 0
        previous = None
        for waypoint_id in trip.waypoint_ids:
            waypoint = waypoints_manager.get_waypoint(waypoint_id)
            if waypoint is None:
                continue
            resolved_count += 1
            if previous is not None:
                total_km += haversine_distance_km(
                    previous.latitude, previous.longitude, waypoint.latitude, waypoint.longitude
                )
            previous = waypoint

        if resolved_count < 2:
            return None
        return total_km

    # ------------------------------------------------------------------
    # Photos
    # ------------------------------------------------------------------

    def add_photo(self, trip_id: str, source_path: Path) -> str:
        """
        Copies an existing image file into trip_photos/<trip_id>/ and
        records its filename on the trip. Import-only (QFileDialog picks
        an existing file) — no camera capture, that needs real Pi camera
        hardware this dev sandbox doesn't have. Raises ValueError if the
        trip doesn't exist; lets a copy failure (e.g. disk full, source
        vanished) propagate as OSError rather than silently no-op, since
        the caller needs to know the photo wasn't actually saved.
        """
        trip = self.get_trip(trip_id)
        if trip is None:
            raise ValueError(f"No trip with id '{trip_id}'.")

        trip_photo_dir = self._photo_root / trip_id
        trip_photo_dir.mkdir(parents=True, exist_ok=True)
        destination = trip_photo_dir / source_path.name
        shutil.copy2(source_path, destination)

        if source_path.name not in trip.photo_filenames:
            trip.photo_filenames.append(source_path.name)
        self._bump_updated_at(trip)
        self._save()
        return source_path.name

    def remove_photo(self, trip_id: str, filename: str) -> Trip:
        """Removes the filename from the trip and deletes the stored copy (not the user's original, if any)."""
        trip = self.get_trip(trip_id)
        if trip is None:
            raise ValueError(f"No trip with id '{trip_id}'.")

        if filename in trip.photo_filenames:
            trip.photo_filenames.remove(filename)
            try:
                (self._photo_root / trip_id / filename).unlink(missing_ok=True)
            except OSError:
                log.warning("Could not delete stored photo copy for trip '%s': %s", trip_id, filename)

        self._bump_updated_at(trip)
        self._save()
        return trip

    def photo_path(self, trip_id: str, filename: str) -> Path:
        """Full on-disk path for a trip's stored photo — for the UI to load as a thumbnail/preview."""
        return self._photo_root / trip_id / filename

    # ------------------------------------------------------------------
    # Logged checkpoints (actual speed/distance, not planned)
    # ------------------------------------------------------------------

    def record_split(self, trip_id: str, waypoint_id: str, timestamp: Optional[datetime] = None) -> Trip:
        """
        Logs "arrived at this waypoint now" — the field-buildable stand-in
        for live GPS tracking (see docs/ROADMAP.md milestone 12.5): the
        user checks in at each waypoint as they reach it, same mental
        model as a compass-and-map hiker logging times at trail
        junctions. `timestamp` defaults to the real current time; passing
        it explicitly exists only for tests.
        """
        trip = self.get_trip(trip_id)
        if trip is None:
            raise ValueError(f"No trip with id '{trip_id}'.")
        logged_at = (timestamp or datetime.now()).isoformat(timespec="seconds")
        trip.splits.append(Split(waypoint_id=waypoint_id, logged_at=logged_at))
        self._bump_updated_at(trip)
        self._save()
        return trip

    def leg_summaries(self, trip_id: str) -> list[LegSummary]:
        """
        One LegSummary per consecutive pair of logged splits, in the
        order they were recorded (not the planned route's order — a
        hiker might check in out of the planned sequence, and that's
        still real data worth summarizing). Splits whose waypoint no
        longer resolves are skipped rather than raising, same as
        planned_route_distance_km().
        """
        trip = self.get_trip(trip_id)
        if trip is None or len(trip.splits) < 2:
            return []

        waypoints_manager = self.context.waypoints
        if waypoints_manager is None:
            return []

        summaries: list[LegSummary] = []
        for previous, current in zip(trip.splits, trip.splits[1:]):
            previous_waypoint = waypoints_manager.get_waypoint(previous.waypoint_id)
            current_waypoint = waypoints_manager.get_waypoint(current.waypoint_id)
            if previous_waypoint is None or current_waypoint is None:
                continue

            distance_km = haversine_distance_km(
                previous_waypoint.latitude,
                previous_waypoint.longitude,
                current_waypoint.latitude,
                current_waypoint.longitude,
            )
            elapsed_hours = (
                datetime.fromisoformat(current.logged_at) - datetime.fromisoformat(previous.logged_at)
            ).total_seconds() / 3600.0
            speed_kmh = (distance_km / elapsed_hours) if elapsed_hours > 0 else None

            summaries.append(
                LegSummary(
                    from_waypoint_id=previous.waypoint_id,
                    to_waypoint_id=current.waypoint_id,
                    distance_km=distance_km,
                    elapsed_hours=elapsed_hours,
                    speed_kmh=speed_kmh,
                )
            )
        return summaries

    def total_distance_km(self, trip_id: str) -> Optional[float]:
        summaries = self.leg_summaries(trip_id)
        if not summaries:
            return None
        return sum(s.distance_km for s in summaries)

    def average_speed_kmh(self, trip_id: str) -> Optional[float]:
        summaries = self.leg_summaries(trip_id)
        total_hours = sum(s.elapsed_hours for s in summaries)
        if not summaries or total_hours <= 0:
            return None
        return sum(s.distance_km for s in summaries) / total_hours
