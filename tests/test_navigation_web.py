"""Navigation's web screen (core/navigation_web.py): waypoints with grid references, distance and bearing, the sun
and the moon."""

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
