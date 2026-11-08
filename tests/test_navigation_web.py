"""Navigation's web screen (core/navigation_web.py): waypoints with grid references, distance and bearing, the sun
and the moon; and a waypoint changed with waypoint.edit, on the page and by voice."""

from datetime import date
from types import SimpleNamespace

from core.navigation_web import screen, sky
from core.waypoint_manager import WaypointManager


def test_waypoints_a_route_and_the_sky(tmp_path):
    book = WaypointManager(SimpleNamespace(), data_dir=tmp_path)
    a = book.add_waypoint("Trailhead", 40.0, -105.0)
    b = book.add_waypoint("Spring", 40.01, -105.0)
    data = screen(SimpleNamespace(waypoints=book), a.waypoint_id, b.waypoint_id, date(2026, 6, 21))
    assert [w["name"] for w in data["waypoints"]] == ["Spring", "Trailhead"]
    assert data["waypoints"][0]["grid"].startswith("13T")
    route = data["route"]
    assert 1.0 < route["km"] < 1.2 and route["toward"] == "N" and route["bearing"] in (0, 360)
    assert data["sky"]["name"] == "Trailhead" and data["sky"]["sunrise"] and data["sky"]["sunset"]
    assert screen(SimpleNamespace(waypoints=None))["waypoints"] == []


def test_the_sky_where_the_sun_never_sets():
    found = sky(80.0, 15.0, date(2026, 6, 21))  # Svalbard in midsummer
    assert found["sunrise"] == "" and found["moon"] in ("New moon", "First quarter", "Full moon", "Last quarter")


def test_a_waypoint_is_renamed_given_a_kind_and_notes_on_the_page_and_by_voice(tmp_path):
    import pytest

    from core.actions import ACTION_TYPES, ActionError
    from core.assistant_actions import AssistantActionRegistry
    from core.assistant_waypoint_actions import register_waypoint_actions

    book = WaypointManager(SimpleNamespace(), data_dir=tmp_path)
    spring = book.add_waypoint("Spring", 40.01, -105.0)
    context = SimpleNamespace(waypoints=book)
    edit = ACTION_TYPES["waypoint.edit"]
    params = {"waypoint_id": spring.waypoint_id, "name": "Upper Spring", "category": "Water Source", "notes": "dry in August"}
    assert edit.describe(context, params) == "Change Spring: call it Upper Spring, kind Water Source, its notes"
    assert edit.execute(context, params) == "Changed Upper Spring."
    w = book.get_waypoint(spring.waypoint_id)
    assert (w.name, w.category, w.notes, w.latitude) == ("Upper Spring", "Water Source", "dry in August", 40.01)
    with pytest.raises(ActionError):
        edit.describe(context, {**params, "name": " "})
    registry = AssistantActionRegistry()
    register_waypoint_actions(registry)
    tool = registry._actions["change_waypoint"].handler
    assert tool(context, {"name": "the upper spring", "new_name": "Spring"}) == "Changed Spring."
    assert book.get_waypoint(spring.waypoint_id).notes == "dry in August"  # what wasn't said stays
    assert tool(context, {"name": "barn"}) == "I don't have a waypoint called 'barn'."
