"""
core.memories_web
===================

Memories' web screen (web/memories.html): one recap per expedition, newest
first (core/memory_manager.py, as the desktop's Memories module shows them):
how long, the distance and pace by activity, the kinds of places visited,
the journal's highlights and how many photos, with "On this day" above when
a past expedition started on today's date, and its route map (`route_map`:
where its trips went, from the checkpoints logged or else the planned
stops, placed on a small map by `project`). Read only; the trips and their
photos are the Expeditions page's.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Optional

MAP_W = 100.0  # the route map's width; its height follows the route's shape


def project(points: list[tuple[float, float]], pad: float = 8.0) -> tuple[list[tuple[float, float]], float]:
    """Pure logic. Latitude/longitude points placed on a small map MAP_W wide (north up, east right, distances true
    across the map: longitude shrinks by the cosine of the latitude), with `pad` around; returns (x, y) per point and
    the map's height. One point sits in the middle of a square map."""
    if not points:
        return [], MAP_W
    mid = math.radians(sum(lat for lat, _ in points) / len(points))
    xs = [lon * math.cos(mid) for _, lon in points]
    ys = [lat for lat, _ in points]
    span_x, span_y = max(xs) - min(xs), max(ys) - min(ys)
    span = max(span_x, span_y)
    if span == 0:
        return [(MAP_W / 2, MAP_W / 2)] * len(points), MAP_W
    scale = (MAP_W - 2 * pad) / span
    height = round(max(span_y * scale + 2 * pad, 30.0), 1)
    left = pad + ((MAP_W - 2 * pad) - span_x * scale) / 2
    top = pad + ((height - 2 * pad) - span_y * scale) / 2
    return [(round(left + (x - min(xs)) * scale, 1), round(top + (max(ys) - y) * scale, 1)) for x, y in zip(xs, ys)], height


def route_map(context, expedition_id: str) -> Optional[dict]:
    """Where an expedition's trips went, for its recap: each trip's checkpoints in the order logged (or its planned
    stops when none were logged), as one path of named points on a small map ({w, h, points: [{x, y, name}]});
    None when no trip has two places to draw."""
    trips, book = getattr(context, "trips", None), getattr(context, "waypoints", None)
    if trips is None or book is None:
        return None
    places = []
    for trip in sorted(trips.trips_for_expedition(expedition_id), key=lambda t: t.start_date or ""):
        ids = [s.waypoint_id for s in trip.splits] or list(trip.waypoint_ids)
        for wid in ids:
            w = book.get_waypoint(wid)
            if w is not None and (not places or places[-1].waypoint_id != w.waypoint_id):
                places.append(w)
    if len(places) < 2:
        return None
    xy, height = project([(w.latitude, w.longitude) for w in places])
    return {"w": MAP_W, "h": height, "points": [{"x": x, "y": y, "name": w.name} for (x, y), w in zip(xy, places)]}


def _recap(r, context=None) -> dict:
    """One expedition's recap (core/memory_manager.ExpeditionRecap) as the page shows it: dates, place, days, distance,
    photos, distance and pace per activity, places by kind (most first), the first three journal highlights, and its
    route map (`route_map`, with a context).
    """
    e = r.expedition
    return {"id": e.expedition_id, "name": e.name, "where": e.location, "start": e.start_date, "end": e.end_date,
            "days": r.duration_days, "km": round(r.total_distance_km, 1), "photos": r.photo_count,
            "activities": [{"kind": s.activity_type, "trips": s.trip_count, "km": round(s.distance_km, 1),
                            "kmh": round(s.average_speed_kmh, 1) if s.average_speed_kmh else None}
                           for s in r.activity_breakdown.values()],
            "places": [{"kind": k, "count": n} for k, n in sorted(r.waypoint_categories_visited.items(),
                                                                  key=lambda kv: -kv[1])],
            "highlights": [j.title for j in r.journal_highlights[:3]],
            "map": route_map(context, e.expedition_id) if context is not None else None}


def screen(context, today: Optional[date] = None) -> dict:
    """Every expedition's recap (with its route map), newest first, and the ones that started on this day in an earlier
    year."""
    book = getattr(context, "memories", None)
    if book is None:
        return {"recaps": [], "on_this_day": []}
    return {"recaps": [_recap(r, context) for r in book.all_recaps()],
            "on_this_day": [_recap(r, context) for r in book.on_this_day(today)]}
