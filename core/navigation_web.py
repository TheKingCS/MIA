"""
core.navigation_web
=====================

Navigation's web screen (web/navigation.html): the waypoints with their
grid references (core/geo_grid.py, MGRS), the distance and bearing from one
to another, and the sun and moon at one of them on a day. The same reading
as the desktop's Navigation module (modules/navigation), assembled here so
the web never computes it (DEC-0017). Adding a waypoint is by voice for now
("add a waypoint called Spring at 18S UJ 23478 06483").
"""

from __future__ import annotations

from datetime import date
from typing import Optional

MOON = ((7, "New moon"), (14, "First quarter"), (21, "Full moon"), (30, "Last quarter"))  # astral's four buckets
COMPASS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def _grid(lat: float, lon: float) -> str:
    """A place's MGRS grid reference (core/geo_grid.py), or "" beyond MGRS's bands (near the poles)."""
    from core.geo_grid import to_mgrs

    try:
        return to_mgrs(lat, lon)
    except ValueError:  # beyond MGRS's UTM bands (the poles)
        return ""


def sky(lat: float, lon: float, day: date) -> dict:
    """Sunrise, sunset (local time) and the moon's phase at a place on a day; the sun's times are "" where it
    doesn't rise or set (inside the polar circles)."""
    from astral import Observer, moon
    from astral.sun import sun

    out = {"sunrise": "", "sunset": "", "moon": next(name for limit, name in MOON if moon.phase(day) < limit)}
    try:
        times = sun(Observer(latitude=lat, longitude=lon), date=day)
        out["sunrise"], out["sunset"] = (f"{times[k].astimezone():%H:%M}" for k in ("sunrise", "sunset"))
    except ValueError:
        pass
    return out


def screen(context, from_id: str = "", to_id: str = "", day: Optional[date] = None) -> dict:
    """Navigation's page data: the waypoints by name with their grids; the route (km, miles, bearing, compass
    point) from `from_id` to `to_id` when both are given and differ; the sky (sunrise, sunset, moon) at `from_id`, else
    at the first waypoint, on `day`; each waypoint's notes and form values, and the Edit form.
    """
    day = day or date.today()
    book = getattr(context, "waypoints", None)
    points = sorted(book.all_waypoints(), key=lambda w: w.name.lower()) if book is not None else []
    from core.waypoint_actions import forms

    shown = [{"id": w.waypoint_id, "name": w.name, "category": w.category, "lat": round(w.latitude, 5),
              "lon": round(w.longitude, 5), "grid": _grid(w.latitude, w.longitude), "notes": w.notes,
              "values": {"name": w.name, "category": w.category, "notes": w.notes}} for w in points]
    out = {"waypoints": shown, "route": None, "sky": None, "day": day.isoformat(), "forms": forms()}
    if book is not None and from_id and to_id and from_id != to_id:
        found = book.distance_and_bearing(from_id, to_id)
        if found is not None:
            km, bearing = found
            out["route"] = {"from": from_id, "to": to_id, "km": round(km, 2), "miles": round(km * 0.621371, 2),
                            "bearing": round(bearing), "toward": COMPASS[int((bearing + 22.5) % 360 // 45)]}
    at = next((w for w in points if w.waypoint_id == from_id), points[0] if points else None)
    if at is not None:
        out["sky"] = {"at": at.waypoint_id, "name": at.name, **sky(at.latitude, at.longitude, day)}
    return out
