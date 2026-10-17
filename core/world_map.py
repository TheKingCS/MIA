"""
core.world_map
================

The world map with fog of war (DEC-0028, the game layer's sixth idea;
Zac, 2026-10-17): the places you've actually been clear the fog, photos
are pinned where they were taken, and new ground earns achievements.

What clears the fog (each a point; the map is tiles at ZOOM, ~2 km):
- **Arrivals**: a trip's splits (you tapped "arrived" at a waypoint).
- **Finished trips**: their planned route, waypoint to waypoint.
- **Photos**: a trip or expedition photo with GPS in it (read here
  from the JPEG's EXIF, no library needed).
- **"I'm Here"**: the person reveals where they're standing (the phone's
  location, only when they press it; `map.checkin`).

Waypoints nobody has reached yet show as "?" pins in the fog: places to
go. `WorldMap` is each person's own (a personal store): their check-ins
and the day each tile was first cleared. It writes through
atomic_write_text, so a check-in can be undone.
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger
from core.map_tile_math import lat_lon_to_tile_xy

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "world_map.json"
ZOOM = 14  # a tile is ~2.4 km across at the equator
REGION_ZOOM = 8  # a "region" is ~150 km across
XP_PER_TILE, XP_CAP = 5, 50

TILE_RANKS = ((1, "First Steps", "👣"), (10, "Wanderer", "🥾"), (25, "Explorer", "🧭"), (50, "Pathfinder", "🗺️"),
              (100, "Ranger", "🏔️"), (250, "Cartographer", "📐"), (500, "World Walker", "🌍"))
REGION_RANKS = ((2, "Day Tripper", "🚗"), (5, "Far And Wide", "✈️"), (10, "Globetrotter", "🌐"))


# ------------------------------------------------------------------ pure logic


def tile_of(lat: float, lon: float, zoom: int = ZOOM) -> tuple[int, int]:
    return lat_lon_to_tile_xy(lat, lon, zoom)


def around(x: int, y: int) -> list[tuple[int, int]]:
    """Pure logic. A tile and the eight around it (where you stood
    clears what you could see)."""
    return [(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]


def along(a: tuple[float, float], b: tuple[float, float], step_km: float = 1.0) -> list[tuple[float, float]]:
    """Pure logic. Points every ~step_km from a to b (a straight line:
    the route between two waypoints)."""
    from core.waypoint_manager import haversine_distance_km

    d = haversine_distance_km(a[0], a[1], b[0], b[1])
    n = max(1, int(math.ceil(d / step_km)))
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]


def tile_km2(y: int, zoom: int = ZOOM) -> float:
    """Pure logic. A tile's area in km² at its latitude."""
    from core.map_tile_math import tile_xy_to_lat_lon

    lat, _lon = tile_xy_to_lat_lon(0, y, zoom)
    side = 40075.016686 * math.cos(math.radians(lat)) / (2 ** zoom)
    return side * side


def ranks(tiles: int, regions: int) -> list[dict]:
    """Pure logic. Every achievement, earned or with how far to go."""
    out = []
    for need, name, icon in TILE_RANKS:
        out.append({"name": name, "icon": icon, "earned": tiles >= need, "need": need, "have": min(tiles, need),
                    "what": f"Clear {need} map {'tile' if need == 1 else 'tiles'}"})
    for need, name, icon in REGION_RANKS:
        out.append({"name": name, "icon": icon, "earned": regions >= need, "need": need, "have": min(regions, need),
                    "what": f"Explore {need} different regions"})
    return out


def _rational(data: bytes, offset: int, endian: str) -> float:
    num, den = struct.unpack(endian + "II", data[offset:offset + 8])
    return num / den if den else 0.0


def exif_gps(data: bytes) -> Optional[tuple[float, float]]:
    """Pure logic. (lat, lon) from a JPEG's EXIF GPS block, or None."""
    try:
        if data[:2] != b"\xff\xd8":
            return None
        i = 2
        while i + 4 <= len(data):
            if data[i] != 0xFF:
                return None
            marker = data[i + 1]
            size = struct.unpack(">H", data[i + 2:i + 4])[0]
            if marker == 0xE1 and data[i + 4:i + 10] == b"Exif\x00\x00":
                return _tiff_gps(data[i + 10:i + 2 + size])
            if marker in (0xDA, 0xD9):
                return None
            i += 2 + size
    except (struct.error, IndexError, ZeroDivisionError):
        return None
    return None


def _tiff_gps(t: bytes) -> Optional[tuple[float, float]]:
    endian = "<" if t[:2] == b"II" else ">"
    ifd0 = struct.unpack(endian + "I", t[4:8])[0]

    def entries(offset):
        count = struct.unpack(endian + "H", t[offset:offset + 2])[0]
        for k in range(count):
            e = offset + 2 + 12 * k
            tag, kind, n = struct.unpack(endian + "HHI", t[e:e + 8])
            yield tag, kind, n, e + 8

    gps_at = next((struct.unpack(endian + "I", t[v:v + 4])[0] for tag, _k, _n, v in entries(ifd0) if tag == 0x8825), None)
    if gps_at is None:
        return None
    found = {}
    for tag, _kind, _n, v in entries(gps_at):
        if tag in (1, 3):
            found[tag] = chr(t[v])
        elif tag in (2, 4):
            at = struct.unpack(endian + "I", t[v:v + 4])[0]
            d, m, s = (_rational(t, at + 8 * j, endian) for j in range(3))
            found[tag] = d + m / 60 + s / 3600
    if 2 not in found or 4 not in found:
        return None
    lat = -found[2] if found.get(1) == "S" else found[2]
    lon = -found[4] if found.get(3) == "W" else found[4]
    if lat == 0 and lon == 0:
        return None
    return round(lat, 6), round(lon, 6)


# ------------------------------------------------------------------ the store


@dataclass
class CheckIn:
    lat: float
    lon: float
    at: str
    label: str = ""


class WorldMap:
    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self.checkins: list[CheckIn] = []
        self.first_seen: dict[str, str] = {}  # "x,y" -> the day it was first cleared
        self._load()

    def _load(self) -> None:
        self.checkins, self.first_seen = [], {}
        if not self._file.exists():
            return
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
            self.checkins = [CheckIn(float(c["lat"]), float(c["lon"]), str(c.get("at") or ""), str(c.get("label") or ""))
                             for c in raw.get("checkins") or []]
            self.first_seen = {str(k): str(v) for k, v in (raw.get("first_seen") or {}).items()}
        except (json.JSONDecodeError, OSError, TypeError, ValueError, KeyError, AttributeError):
            log.exception("world_map.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        self._load()

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"checkins": [asdict(c) for c in self.checkins],
                                                  "first_seen": self.first_seen}, indent=2, ensure_ascii=False))

    def check_in(self, lat: float, lon: float, label: str = "") -> CheckIn:
        c = CheckIn(round(lat, 6), round(lon, 6), datetime.now().isoformat(timespec="seconds"), label)
        self.checkins.append(c)
        self._save()
        return c

    def see(self, tiles: dict[str, str]) -> list[str]:
        """Remember the day each tile was first cleared; returns the new ones."""
        new = [k for k in tiles if k not in self.first_seen]
        for k in new:
            self.first_seen[k] = tiles[k]
        if new:
            self._save()
        return new


# ------------------------------------------------------------------ what's been explored


def _waypoints(context) -> dict:
    w = getattr(context, "waypoints", None)
    return {p.waypoint_id: p for p in w.all_waypoints()} if w is not None else {}


def points(context) -> list[dict]:
    """Every place that clears fog: {lat, lon, kind, label, day, reveal}
    where reveal is "around" (you were there) or "path" (on a route)."""
    out: list[dict] = []
    wps = _waypoints(context)
    trips = getattr(context, "trips", None)
    if trips is not None:
        for trip in trips.all_trips():
            for s in trip.splits:
                p = wps.get(s.waypoint_id)
                if p is not None:
                    out.append({"lat": p.latitude, "lon": p.longitude, "kind": "arrival", "label": p.name,
                                "day": (s.logged_at or "")[:10], "reveal": "around"})
            if trip.status == "completed":
                route = [wps[w] for w in trip.waypoint_ids if w in wps]
                day = trip.end_date or trip.start_date or (trip.updated_at or "")[:10]
                for a, b in zip(route, route[1:]):
                    for lat, lon in along((a.latitude, a.longitude), (b.latitude, b.longitude)):
                        out.append({"lat": lat, "lon": lon, "kind": "route", "label": trip.name, "day": day,
                                    "reveal": "path"})
                for p in route:
                    out.append({"lat": p.latitude, "lon": p.longitude, "kind": "arrival", "label": p.name,
                                "day": day, "reveal": "around"})
    out += [{**pin, "reveal": "around"} for pin in photo_pins(context)]
    book = getattr(context, "world_map", None)
    if book is not None:
        for c in book.checkins:
            out.append({"lat": c.lat, "lon": c.lon, "kind": "checkin", "label": c.label or "I was here",
                        "day": c.at[:10], "reveal": "around"})
    return out


def photo_pins(context) -> list[dict]:
    """Photos on expeditions and trips that know where they were taken."""
    from core.expedition_media import media, path_of

    exps = getattr(context, "expeditions", None)
    if exps is None:
        return []
    pins = []
    for x in exps.all_expeditions():
        try:
            items = media(context, x.expedition_id)
        except (OSError, ValueError):
            continue
        for m in items:
            if m["kind"] != "image" or not m["name"].lower().endswith((".jpg", ".jpeg")):
                continue
            try:
                with open(path_of(context, x.expedition_id, m["ref"]), "rb") as f:
                    where = exif_gps(f.read(256 * 1024))
            except (OSError, ValueError):
                continue
            if where:
                pins.append({"lat": where[0], "lon": where[1], "kind": "photo", "label": x.name, "day": m["added"],
                             "expedition_id": x.expedition_id, "ref": m["ref"], "name": m["name"]})
    return pins


def explored(pts: list[dict]) -> dict[str, str]:
    """Pure logic. "x,y" -> the earliest day it was cleared."""
    tiles: dict[str, str] = {}
    for p in pts:
        x, y = tile_of(p["lat"], p["lon"])
        for tx, ty in (around(x, y) if p["reveal"] == "around" else [(x, y)]):
            key = f"{tx},{ty}"
            day = p.get("day") or ""
            if key not in tiles or (day and day < tiles[key]):
                tiles[key] = day
    return tiles


def regions(tiles: dict[str, str]) -> int:
    """Pure logic. How many REGION_ZOOM tiles the explored ones fall in."""
    shift = ZOOM - REGION_ZOOM
    return len({(int(k.split(",")[0]) >> shift, int(k.split(",")[1]) >> shift) for k in tiles})


def world_page(context, today: Optional[date] = None) -> dict:
    """Expeditions → World Map: the cleared tiles, pins, how much ground
    that is, the achievements, and the newest discoveries."""
    today = today or date.today()
    pts = points(context)
    tiles = explored(pts)
    book = getattr(context, "world_map", None)
    if book is not None:
        book.see({k: v or today.isoformat() for k, v in tiles.items()})
    first = dict(book.first_seen) if book is not None else {}
    area = sum(tile_km2(int(k.split(",")[1])) for k in tiles)
    n_regions = regions(tiles)
    pins = [p for p in pts if p["kind"] in ("photo", "checkin")]
    seen_wp = {(round(p["lat"], 5), round(p["lon"], 5)) for p in pts if p["kind"] == "arrival"}
    unknown = [{"lat": w.latitude, "lon": w.longitude, "kind": "unknown", "label": w.name}
               for w in _waypoints(context).values() if (round(w.latitude, 5), round(w.longitude, 5)) not in seen_wp]
    arrivals = {}
    for p in pts:
        if p["kind"] == "arrival":
            arrivals[(round(p["lat"], 5), round(p["lon"], 5))] = {"lat": p["lat"], "lon": p["lon"], "kind": "arrival",
                                                                  "label": p["label"], "day": p["day"]}
    newest = sorted(((first.get(k) or v, k) for k, v in tiles.items()), reverse=True)
    recent_days = sorted({d for d, _k in newest if d}, reverse=True)[:5]
    return {
        "available": True, "zoom": ZOOM, "as_of": today.isoformat(),
        "tiles": [[int(k.split(",")[0]), int(k.split(",")[1])] for k in sorted(tiles)],
        "pins": [{k: v for k, v in p.items() if k != "reveal"} for p in pins] + list(arrivals.values()) + unknown,
        "stats": {"tiles": len(tiles), "km2": round(area, 1), "regions": n_regions,
                  "places": len(arrivals), "photos": sum(1 for p in pins if p["kind"] == "photo"),
                  "to_discover": len(unknown)},
        "ranks": ranks(len(tiles), n_regions),
        "discoveries": [{"day": d, "tiles": sum(1 for x, _k in newest if x == d)} for d in recent_days],
        "can_check_in": book is not None,
    }
