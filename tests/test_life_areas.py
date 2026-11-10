"""
tests.test_life_areas
=======================

The life state's `areas` section (core/life_areas.py): each area reads its
store live, says PLANNED without one, never breaks the life state when one
fails, keeps a child out of the money areas, and every area names a store
MIA really has, and the homestead area reads its snapshots' critical alerts.
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
    """The shop's books, business, insurance, obligations and business use are left out for a child, as finances
    are."""
    adult = life_areas.areas(SimpleNamespace(), TODAY)
    child = life_areas.areas(SimpleNamespace(), TODAY, child=True)
    money = {a.key for a in life_areas.AREAS if a.adults_only}
    assert money == {"shop_books", "business", "insurance", "obligations", "business_use"}
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


def test_the_homestead_area_counts_its_systems_and_names_open_critical_alerts():
    """Two systems reporting, one with two critical alerts in its summary and one with none given: two systems, two
    alerts, named as what's next; none open, nothing next."""
    snap = lambda data: SimpleNamespace(data=data)  # noqa: E731
    homestead = SimpleNamespace(all_latest_snapshots=lambda: [snap({"summary": {"critical_alert_count": 2}}),
                                                              snap({"tanks": []})])
    found = life_areas.areas(SimpleNamespace(homestead=homestead), TODAY)["homestead"]
    assert found["counts"] == {"systems": 2, "critical_alerts": 2}
    assert found["next"] == "2 critical alerts at the homestead"
    quiet = SimpleNamespace(all_latest_snapshots=lambda: [snap({"summary": {"critical_alert_count": 0}})])
    assert life_areas.areas(SimpleNamespace(homestead=quiet), TODAY)["homestead"]["next"] is None


def test_directions_workplaces_worlds_and_questlines_are_areas_too():
    """Each reads its store: the active directions, the shifts cleared this week and the next planned one, the
    campaigns going, and the questline under way with its chapter."""
    directions = SimpleNamespace(directions=[SimpleNamespace(active=True), SimpleNamespace(active=False)])
    dungeon = SimpleNamespace(
        dungeons=[SimpleNamespace(dungeon_id="d1", name="The mill")],
        runs=[SimpleNamespace(dungeon_id="d1", date="2026-11-05", status="cleared"),
              SimpleNamespace(dungeon_id="d1", date="2026-10-01", status="cleared"),
              SimpleNamespace(dungeon_id="d1", date="2026-11-09", status="planned")])
    worlds = SimpleNamespace(campaigns=[SimpleNamespace(status="active"), SimpleNamespace(status="paused")])
    quest = SimpleNamespace(name="The long road", started_on="2026-11-01", finished=False, current=lambda: 1)
    quests = SimpleNamespace(quests=[quest, SimpleNamespace(name="Unstarted", started_on="", finished=False)])
    found = life_areas.areas(SimpleNamespace(direction=directions, dungeon=dungeon, living_worlds=worlds,
                                             quest_book=quests), TODAY)
    assert found["directions"]["counts"] == {"directions": 2, "active": 1}
    assert found["workplaces"]["counts"] == {"workplaces": 1, "shifts_this_week": 1}
    assert found["workplaces"]["next"] == "The mill on 2026-11-09"
    assert found["worlds"]["counts"] == {"campaigns": 2, "active": 1}
    assert found["questlines"] == {"status": "REAL", "source": "core/questlines.py",
                                   "counts": {"started": 1, "finished": 0}, "next": "The long road, chapter 2"}


def test_the_creative_game_and_fitness_stores_are_areas_with_their_counts():
    """Art, creations, plans, play, the world map, boss battles and the fitness plan each give their counts; play
    counts only this week's entries as this week."""
    context = SimpleNamespace(
        art=SimpleNamespace(items=[{}, {}]),
        creations=SimpleNamespace(items=[{"status": "published"}, {"status": "draft"}]),
        plans=SimpleNamespace(plans={"p1": {}}),
        recreation=SimpleNamespace(entries=[{"date": "2026-11-06"}, {"date": "2026-10-01"}]),
        world_map=SimpleNamespace(checkins=[1, 2, 3], first_seen={"1,2": "2026-11-01"}),
        boss_book=SimpleNamespace(defeated={"b1": "2026-11-02"}),
        fitness=SimpleNamespace(plan={"training": {"days": ["Mon", "Thu"]}}))
    found = life_areas.areas(context, TODAY)
    assert found["art"]["counts"] == {"paintings": 2}
    assert found["creations"]["counts"] == {"creations": 2, "published": 1}
    assert found["plans"]["counts"] == {"plans": 1}
    assert found["play"]["counts"] == {"played": 2, "this_week": 1}
    assert found["world_map"]["counts"] == {"checkins": 3, "cleared": 1}
    assert found["bosses"]["counts"] == {"defeated": 1}
    assert found["fitness"]["counts"] == {"training_days": 2}
