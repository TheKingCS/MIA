"""
tests.test_expeditions_module
================================

Unit tests for modules.expeditions.module's pure functions, same style
as tests/test_navigation_module.py (no Qt event loop, no fixtures).
"""

from __future__ import annotations

from core.expedition_manager import Expedition
from core.trip_manager import Trip
from modules.expeditions.module import format_expedition_row, format_trip_row


def test_format_expedition_row_single_day():
    expedition = Expedition(
        expedition_id="exp1",
        name="Sawtooth Weekend",
        start_date="2026-08-14",
        end_date="2026-08-14",
        location="Sawtooth Wilderness",
    )
    assert format_expedition_row(expedition) == "Sawtooth Weekend  [2026-08-14]  (Sawtooth Wilderness)"


def test_format_expedition_row_date_range():
    expedition = Expedition(
        expedition_id="exp1",
        name="Sawtooth Weekend",
        start_date="2026-08-14",
        end_date="2026-08-16",
        location="",
    )
    assert format_expedition_row(expedition) == "Sawtooth Weekend  [2026-08-14 - 2026-08-16]"


def test_format_expedition_row_no_location():
    expedition = Expedition(expedition_id="exp1", name="Solo Trip", start_date="2026-08-14")
    assert format_expedition_row(expedition) == "Solo Trip  [2026-08-14]"


def test_format_trip_row():
    trip = Trip(
        trip_id="t1",
        expedition_id="exp1",
        name="Hike In",
        start_date="2026-08-14",
        status="planned",
    )
    assert format_trip_row(trip) == "Hike In  [2026-08-14]  (planned)"


def test_format_trip_row_with_activity_type():
    trip = Trip(
        trip_id="t1",
        expedition_id="exp1",
        name="Evening Cast",
        start_date="2026-08-14",
        status="planned",
        activity_type="Fishing",
    )
    assert format_trip_row(trip) == "[Fishing] Evening Cast  [2026-08-14]  (planned)"
