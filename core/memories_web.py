"""
core.memories_web
===================

Memories' web screen (web/memories.html): one recap per expedition, newest
first (core/memory_manager.py, as the desktop's Memories module shows them):
how long, the distance and pace by activity, the kinds of places visited,
the journal's highlights and how many photos, with "On this day" above when
a past expedition started on today's date. Read only; the trips and their
photos are the Expeditions page's.
"""

from __future__ import annotations

from datetime import date
from typing import Optional


def _recap(r) -> dict:
    e = r.expedition
    return {"id": e.expedition_id, "name": e.name, "where": e.location, "start": e.start_date, "end": e.end_date,
            "days": r.duration_days, "km": round(r.total_distance_km, 1), "photos": r.photo_count,
            "activities": [{"kind": s.activity_type, "trips": s.trip_count, "km": round(s.distance_km, 1),
                            "kmh": round(s.average_speed_kmh, 1) if s.average_speed_kmh else None}
                           for s in r.activity_breakdown.values()],
            "places": [{"kind": k, "count": n} for k, n in sorted(r.waypoint_categories_visited.items(),
                                                                  key=lambda kv: -kv[1])],
            "highlights": [j.title for j in r.journal_highlights[:3]]}


def screen(context, today: Optional[date] = None) -> dict:
    book = getattr(context, "memories", None)
    if book is None:
        return {"recaps": [], "on_this_day": []}
    return {"recaps": [_recap(r) for r in book.all_recaps()],
            "on_this_day": [_recap(r) for r in book.on_this_day(today)]}
