"""
core.memory_manager
======================

Memories — docs/ROADMAP.md milestone v0.17, the first of three new
subsystems from the 2026-07-14 wearable-companion vision update (see
docs/VISION.md). A **read-only aggregation service**, deliberately
unlike every other core manager in this project: it owns no persisted
file of its own and computes an `ExpeditionRecap` on demand from
Expedition/Trip/Waypoint/Journal data that already exists, so it can
never go stale relative to those records and never needs a migration
when their schemas change.

Distance/pace come from `TripManager.total_distance_km()`/
`average_speed_kmh()` — the *logged* checkpoints (actual data), not
`planned_route_distance_km()` (an upfront estimate) — a recap should
describe what happened, not what was planned. "Waypoints visited"
unions each trip's logged split waypoints with its planned route
waypoints, since without live GPS (still an open hardware question per
HARDWARE.md) a logged split is the only "this actually happened" signal
this app has, and a trip with no recorded splits yet (common today)
should still show its planned campsites/trailheads rather than an
empty recap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from core.app_context import AppContext
from core.expedition_manager import Expedition
from core.journal_manager import JournalEntry


@dataclass
class ActivityStats:
    activity_type: str
    trip_count: int = 0
    distance_km: float = 0.0
    total_hours: float = 0.0

    @property
    def average_speed_kmh(self) -> Optional[float]:
        if self.total_hours <= 0:
            return None
        return self.distance_km / self.total_hours


@dataclass
class ExpeditionRecap:
    expedition: Expedition
    duration_days: Optional[int]
    activity_breakdown: dict[str, ActivityStats] = field(default_factory=dict)
    waypoint_categories_visited: dict[str, int] = field(default_factory=dict)
    journal_highlights: list[JournalEntry] = field(default_factory=list)
    photo_filenames: list[tuple[str, str]] = field(default_factory=list)  # (trip_id, filename)

    @property
    def photo_count(self) -> int:
        return len(self.photo_filenames)

    @property
    def total_distance_km(self) -> float:
        return sum(stats.distance_km for stats in self.activity_breakdown.values())


class MemoryManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context

    def recap_for_expedition(self, expedition_id: str) -> Optional[ExpeditionRecap]:
        expedition = self.context.expeditions.get_expedition(expedition_id)
        if expedition is None:
            return None

        trips = self.context.trips.trips_for_expedition(expedition_id)

        activity_breakdown: dict[str, ActivityStats] = {}
        waypoint_categories_visited: dict[str, int] = {}
        journal_highlights: list[JournalEntry] = []
        photo_filenames: list[tuple[str, str]] = []

        for trip in trips:
            activity_type = trip.activity_type or "Other"
            stats = activity_breakdown.setdefault(activity_type, ActivityStats(activity_type=activity_type))
            stats.trip_count += 1

            distance_km = self.context.trips.total_distance_km(trip.trip_id)
            if distance_km:
                stats.distance_km += distance_km
                # average_speed_kmh() is distance / elapsed hours over the
                # same leg_summaries() this distance came from, so hours is
                # recoverable as distance/speed rather than re-deriving it
                # from leg_summaries() a second time here.
                speed_kmh = self.context.trips.average_speed_kmh(trip.trip_id)
                if speed_kmh:
                    stats.total_hours += distance_km / speed_kmh

            visited_waypoint_ids = set(trip.waypoint_ids) | {s.waypoint_id for s in trip.splits}
            for waypoint_id in visited_waypoint_ids:
                waypoint = self.context.waypoints.get_waypoint(waypoint_id)
                if waypoint is None:
                    continue
                category = waypoint.category or "Uncategorized"
                waypoint_categories_visited[category] = waypoint_categories_visited.get(category, 0) + 1

            journal_highlights.extend(self.context.journal.entries_for_trip(trip.trip_id))
            photo_filenames.extend((trip.trip_id, filename) for filename in trip.photo_filenames)

        journal_highlights.sort(key=lambda e: e.updated_at, reverse=True)

        return ExpeditionRecap(
            expedition=expedition,
            duration_days=self._duration_days(expedition, trips),
            activity_breakdown=activity_breakdown,
            waypoint_categories_visited=waypoint_categories_visited,
            journal_highlights=journal_highlights,
            photo_filenames=photo_filenames,
        )

    def all_recaps(self) -> list[ExpeditionRecap]:
        """Most-recent-start-date first — matches how Memories is naturally browsed."""
        recaps = [
            self.recap_for_expedition(expedition.expedition_id)
            for expedition in self.context.expeditions.all_expeditions()
        ]
        return sorted(
            (r for r in recaps if r is not None),
            key=lambda r: r.expedition.start_date,
            reverse=True,
        )

    def on_this_day(self, today: Optional[date] = None) -> list[ExpeditionRecap]:
        """
        Expeditions whose start_date matches today's month/day in a
        prior year — a lightweight extra, not the core Memories feature
        (see docs/ROADMAP.md's v0.17 breakdown). `today` is only ever
        passed explicitly by tests; production always uses the real
        current date.
        """
        today = today or date.today()
        matches = []
        for recap in self.all_recaps():
            parsed = self._parse_date(recap.expedition.start_date)
            if parsed is None:
                continue
            if parsed.month == today.month and parsed.day == today.day and parsed.year != today.year:
                matches.append(recap)
        return matches

    @staticmethod
    def _parse_date(value: str) -> Optional[date]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None

    def _duration_days(self, expedition: Expedition, trips: list) -> Optional[int]:
        start = self._parse_date(expedition.start_date)
        end = self._parse_date(expedition.end_date) or start
        if start is not None and end is not None:
            return (end - start).days + 1

        # Fall back to the span covered by this expedition's trips when
        # the Expedition record itself has no dates set.
        trip_dates = [self._parse_date(t.start_date) for t in trips]
        trip_dates = [d for d in trip_dates if d is not None]
        if not trip_dates:
            return None
        return (max(trip_dates) - min(trip_dates)).days + 1
