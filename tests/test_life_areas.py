"""
tests.test_life_areas
=======================

The life state's `areas` section (core/life_areas.py): each area reads its
store live, says PLANNED without one, never breaks the life state when one
fails, keeps a child out of the money areas, and every area names a store
MIA really has.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from core import life_areas

TODAY = date(2026, 11, 7)


def _event(title, day):
    """A stand-in calendar event."""
    return SimpleNamespace(title=title, date=day)


def test_areas_read_their_stores_and_say_whats_next():
    """The calendar counts this week's events and names the next; a store that isn't here is PLANNED; one that
    fails is empty, not an error."""
    calendar = SimpleNamespace(all_events=lambda: [_event("Dentist", "2026-11-10"), _event("Old", "2026-10-01"),
                                                   _event("Later", "2026-12-25")])
    broken = SimpleNamespace(all_items=lambda: 1 / 0)
    context = SimpleNamespace(calendar=calendar, inventory=broken)
    found = life_areas.areas(context, TODAY)
    assert found["calendar"] == {"status": "REAL", "source": "core/calendar_manager.py",
                                 "counts": {"events": 3, "this_week": 1}, "next": "Dentist on 2026-11-10"}
    assert found["inventory"] == {"status": "REAL", "source": "core/inventory_manager.py", "counts": {}, "next": None}
    assert found["trips"]["status"] == "PLANNED" and found["trips"]["counts"] == {}


def test_a_child_gets_no_money_areas():
    """The shop's books, business, insurance and obligations are left out for a child, as finances are."""
    adult = life_areas.areas(SimpleNamespace(), TODAY)
    child = life_areas.areas(SimpleNamespace(), TODAY, child=True)
    money = {a.key for a in life_areas.AREAS if a.adults_only}
    assert money == {"shop_books", "business", "insurance", "obligations"}
    assert money <= set(adult) and not money & set(child)


def test_every_area_reads_a_store_mia_has():
    """Each area's store is a personal or household store, and its source file exists."""
    from pathlib import Path

    from core.personal_data import HOUSEHOLD_STORES, PERSONAL_STORES

    stores = {n for n, _c in PERSONAL_STORES + HOUSEHOLD_STORES}
    root = Path(__file__).resolve().parent.parent
    for area in life_areas.AREAS:
        assert area.store in stores, area.key
        assert (root / area.source).exists(), area.source
    assert len({a.key for a in life_areas.AREAS}) == len(life_areas.AREAS)
