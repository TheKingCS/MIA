"""
core.gps_tracks
=================

Tracks (build plan step 14, DEC-0099): a walk, a ride or a drive as points
with times, from a GPX file (what phones, watches and GPS units export).
Worked out in code (`stats()`): distance (haversine, between successive
points), climb and descent (changes under `CLIMB_NOISE` metres ignored, as
GPS elevation jitters), elapsed and moving time, and where it started and
ended as MGRS grid references (core/geo_grid.py). A track goes into the TAK
data package as a line (core/tak.py).

Where a person went is theirs: tracks live in their own folder
(`gps_tracks.json`, a personal store).
"""

from __future__ import annotations

from core import life_events

import json
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.waypoint_manager import haversine_distance_km

FILE_NAME = "gps_tracks.json"
CLIMB_NOISE = 3.0  # metres
MOVING_KMH = 1.0  # slower than this between two points counts as stopped
MAX_POINTS = 20_000


class TrackError(ValueError):
    """A file that isn't a GPX track."""


def parse_gpx(text: str) -> tuple[str, list[dict]]:
    """Pure logic. (the track's name, [{lat, lon, ele, time}]) from GPX 1.0 or 1.1 (track points, else route points)."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as problem:
        raise TrackError("That isn't a GPX file.") from problem
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
    name = (root.findtext(f"{ns}trk/{ns}name") or root.findtext(f"{ns}metadata/{ns}name") or "").strip()
    points = []
    for tag in ("trkpt", "rtept"):
        for pt in root.iter(f"{ns}{tag}"):
            try:
                lat, lon = float(pt.get("lat")), float(pt.get("lon"))
            except (TypeError, ValueError):
                continue
            ele = pt.findtext(f"{ns}ele")
            points.append({"lat": lat, "lon": lon, "ele": float(ele) if ele not in (None, "") else None,
                           "time": (pt.findtext(f"{ns}time") or "").strip()})
        if points:
            break
    if len(points) < 2:
        raise TrackError("That GPX file has no track in it.")
    return name, points[:MAX_POINTS]


def _time(text: str) -> Optional[datetime]:
    """A GPX timestamp as a datetime (a trailing Z read as UTC), or None."""
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def stats(points: list[dict]) -> dict:
    """Pure logic. Distance, climb, descent, elapsed and moving time, start and end grids."""
    from core.geo_grid import GridError, to_mgrs

    km = climb = descent = moving = 0.0
    base = points[0]["ele"]
    for a, b in zip(points, points[1:]):
        step = haversine_distance_km(a["lat"], a["lon"], b["lat"], b["lon"])
        km += step
        ta, tb = _time(a["time"]), _time(b["time"])
        if ta and tb and tb > ta:
            hours = (tb - ta).total_seconds() / 3600
            if step / hours >= MOVING_KMH:
                moving += hours
        if b["ele"] is not None:
            if base is None:
                base = b["ele"]
            elif b["ele"] - base >= CLIMB_NOISE:
                climb, base = climb + b["ele"] - base, b["ele"]
            elif base - b["ele"] >= CLIMB_NOISE:
                descent, base = descent + base - b["ele"], b["ele"]
    start, end = _time(points[0]["time"]), _time(points[-1]["time"])

    def grid(p) -> str:
        try:
            return to_mgrs(p["lat"], p["lon"], 4)
        except GridError:
            return ""
    return {"km": round(km, 2), "climb_m": round(climb), "descent_m": round(descent),
            "hours": round((end - start).total_seconds() / 3600, 2) if start and end and end > start else None,
            "moving_hours": round(moving, 2) if moving else None, "start": grid(points[0]), "end": grid(points[-1]),
            "date": start.date().isoformat() if start else "", "points": len(points)}


def describe(track: dict) -> str:
    """A track said in a line: its name and date, distance, climb and descent, time taken (and time moving), and where
    it started and ended.
    """
    s = track["stats"]
    parts = [f"{s['km']:g} km"]
    if s["climb_m"]:
        parts.append(f"{s['climb_m']} m up, {s['descent_m']} m down")
    if s["hours"]:
        h, m = divmod(round(s["hours"] * 60), 60)
        parts.append(f"{h} h {m:02d} min" + (f" ({round(s['moving_hours'] * 60)} min moving)" if s["moving_hours"] else ""))
    return f"{track['name']}" + (f" ({s['date']})" if s["date"] else "") + ": " + ", ".join(parts) + \
        (f"; from {s['start']} to {s['end']}" if s["start"] else "") + "."


_LAST = re.compile(r"^(?:how (?:far|long) (?:was|did i (?:go|hike|walk|run|ride|drive)(?: on)?) )?(?:my )?"
                   r"(?:last|latest) (?:track|hike|walk|run|ride|drive|trip)[?.!]*$", re.IGNORECASE)


def reply(context, text: str) -> Optional[str]:
    """"how far was my last hike?", "my last track": the latest track, in numbers. None otherwise."""
    store = getattr(context, "gps_tracks", None)
    if store is None or not _LAST.match(" ".join(str(text or "").split())):
        return None
    latest = store.latest()
    return describe(latest) if latest else "No tracks yet. Send me a GPX file from your phone or GPS."


class GpsTracks:
    """One person's tracks (context.gps_tracks)."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads the tracks from the person's own folder (gps_tracks.json, or data/ by default)."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parent.parent / "data"
        self._file = self.data_dir / FILE_NAME
        self.tracks: list[dict] = []
        self._load()

    def _load(self) -> None:
        """Reads the tracks; a missing or unreadable file gives none."""
        try:
            self.tracks = json.loads(self._file.read_text(encoding="utf-8")).get("tracks", [])
        except (OSError, ValueError):
            self.tracks = []

    def _save(self) -> None:
        """Writes the tracks atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"tracks": self.tracks}, ensure_ascii=False))

    @life_events.on_change("track_added", "a track", "track")
    def add_gpx(self, text: str, name: str = "") -> dict:
        """Keeps a track from a GPX file: its points, worked-out stats, a name (the one given, the file's, or A track),
        and when it was added.
        """
        found_name, points = parse_gpx(text)
        track = {"id": uuid.uuid4().hex[:10], "name": (name or found_name or "A track").strip()[:80],
                 "points": points, "stats": stats(points), "added": datetime.now().isoformat(timespec="seconds")}
        self.tracks.append(track)
        self._save()
        return track

    @life_events.on_change("track_removed", "a track", "track")
    def delete(self, track_id: str) -> None:
        """Removes a track."""
        self.tracks = [t for t in self.tracks if t["id"] != track_id]
        self._save()

    def latest(self) -> Optional[dict]:
        """The most recent track (by its date, else when it was added), or None."""
        return max(self.tracks, key=lambda t: t["stats"].get("date") or t["added"]) if self.tracks else None
