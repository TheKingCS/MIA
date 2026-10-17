"""
core.places
=============

Location quests (DEC-0028, the game layer's thirteenth idea; Zac,
2026-10-17): arrive at the gym and your workout opens; walk into the
store and your grocery list is up.

A person's places (a personal store): a name, where it is, how close
counts as "here", and what happens on arrival (ARRIVALS). Where you are
is only ever checked on your own device, while MIA is open and only
after you switch it on (Settings → Location quests, `places.watch`):
web/places.js compares the phone's position with these places itself
and nothing about where you are is sent anywhere until you arrive at
one of them and say yes (`place.arrive`), which clears the fog there on
the world map (core/world_map.py) too. It writes through
atomic_write_text, so adding, removing and arriving can be undone.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "places.json"
DEFAULT_RADIUS_M = 150

# What arriving does: (label, what MIA says, the screen it opens).
ARRIVALS = {
    "Start My Workout": ("Your workout's ready. Let's go.", "workout.html#today"),
    "Show My Grocery List": ("Here's your grocery list.", "kitchen.html#grocery"),
    "Show My Missions": ("Here's what's on for today.", "missions.html#active"),
    "Open The Greenhouse": ("Here's the greenhouse.", "greenhouse.html"),
    "Open The Workshop": ("Here's the workshop.", "workshop.html"),
    "Just Remind Me": ("", ""),
}


@dataclass
class Place:
    place_id: str
    name: str
    lat: float
    lon: float
    radius_m: int = DEFAULT_RADIUS_M
    on_arrive: str = "Just Remind Me"
    note: str = ""
    last_arrived: str = ""
    arrivals: int = 0


class Places:
    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self.places: list[Place] = []
        self._load()

    def _load(self) -> None:
        self.places = []
        if not self._file.exists():
            return
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
            fields = Place.__dataclass_fields__
            self.places = [Place(**{k: v for k, v in p.items() if k in fields}) for p in raw.get("places") or []]
        except (json.JSONDecodeError, OSError, TypeError, ValueError, AttributeError):
            log.exception("places.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        self._load()

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"places": [asdict(p) for p in self.places]}, indent=2,
                                                 ensure_ascii=False))

    def get(self, place_id: str) -> Optional[Place]:
        return next((p for p in self.places if p.place_id == place_id), None)

    def add(self, name: str, lat: float, lon: float, radius_m: int = DEFAULT_RADIUS_M, on_arrive: str = "Just Remind Me",
            note: str = "") -> Place:
        place = Place(uuid.uuid4().hex[:10], name, round(lat, 6), round(lon, 6), int(radius_m), on_arrive, note)
        self.places.append(place)
        self._save()
        return place

    def update(self, place_id: str, **fields) -> Place:
        place = self.get(place_id)
        if place is None:
            raise ValueError("No such place.")
        for key, value in fields.items():
            if key in Place.__dataclass_fields__ and key != "place_id":
                setattr(place, key, value)
        self._save()
        return place

    def delete(self, place_id: str) -> None:
        self.places = [p for p in self.places if p.place_id != place_id]
        self._save()

    def arrived(self, place_id: str) -> Place:
        place = self.get(place_id)
        if place is None:
            raise ValueError("No such place.")
        place.last_arrived = datetime.now().isoformat(timespec="seconds")
        place.arrivals += 1
        self._save()
        return place


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Pure logic. Meters between two points (the same great-circle math
    web/places.js uses on the phone)."""
    from core.waypoint_manager import haversine_distance_km

    return haversine_distance_km(lat1, lon1, lat2, lon2) * 1000


def arrival(place: Place) -> dict:
    """What arriving at this place does, for the phone: the line, the screen."""
    say, opens = ARRIVALS.get(place.on_arrive, ARRIVALS["Just Remind Me"])
    line = f"📍 You're at {place.name}." + (f" {say}" if say else "") + (f" {place.note}" if place.note else "")
    return {"say": line, "open": opens, "label": place.on_arrive if opens else "OK"}


def watched(context) -> list[dict]:
    """The places the phone watches for (only when the person switched
    location quests on): where they are and what arriving does."""
    from core import person_settings

    book = getattr(context, "places", None)
    if book is None or not person_settings.get(context, "places.watch", False):
        return []
    return [{"id": p.place_id, "name": p.name, "lat": p.lat, "lon": p.lon, "radius": p.radius_m, **arrival(p)}
            for p in book.places]


def places_page(context) -> dict:
    from core import person_settings

    book = getattr(context, "places", None)
    if book is None:
        return {"available": False}
    return {
        "available": True, "watching": bool(person_settings.get(context, "places.watch", False)),
        "places": [{"id": p.place_id, "name": p.name, "lat": p.lat, "lon": p.lon, "radius": p.radius_m,
                    "on_arrive": p.on_arrive, "note": p.note, "last_arrived": p.last_arrived[:10],
                    "arrivals": p.arrivals} for p in book.places],
        "arrivals": list(ARRIVALS),
        "default_radius": DEFAULT_RADIUS_M,
    }
