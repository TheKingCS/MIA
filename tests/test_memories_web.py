"""Memories' web screen (core/memories_web.py): a recap per expedition, on this day, and a recap's route map."""

from types import SimpleNamespace

from core.memories_web import screen
from core.memory_manager import ActivityStats, ExpeditionRecap


def test_recaps_and_on_this_day():
    e = SimpleNamespace(expedition_id="e1", name="Elk Creek", location="the high country", start_date="2025-11-06",
                        end_date="2025-11-08")
    recap = ExpeditionRecap(expedition=e, duration_days=3,
                            activity_breakdown={"hike": ActivityStats("hike", 2, 18.44, 6.0)},
                            waypoint_categories_visited={"Water": 2, "Camp": 3},
                            journal_highlights=[SimpleNamespace(title="Saw a moose")],
                            photo_filenames=[("t1", "a.jpg"), ("t1", "b.jpg")])
    book = SimpleNamespace(all_recaps=lambda: [recap], on_this_day=lambda today=None: [recap])
    data = screen(SimpleNamespace(memories=book))
    shown = data["recaps"][0]
    assert (shown["km"], shown["photos"], shown["days"]) == (18.4, 2, 3)
    assert shown["activities"] == [{"kind": "hike", "trips": 2, "km": 18.4, "kmh": 3.1}]
    assert [p["kind"] for p in shown["places"]] == ["Camp", "Water"] and shown["highlights"] == ["Saw a moose"]
    assert data["on_this_day"][0]["name"] == "Elk Creek"
    assert screen(SimpleNamespace(memories=None)) == {"recaps": [], "on_this_day": []}


def test_a_recaps_route_map_follows_the_checkpoints_north_up(tmp_path):
    from core.memories_web import MAP_W, project, route_map
    from core.trip_manager import TripManager
    from core.waypoint_manager import WaypointManager

    xy, h = project([(45.0, -93.0), (45.01, -93.0)])
    assert xy[0][1] > xy[1][1] and xy[0][0] == xy[1][0] == MAP_W / 2  # north is up; a north-south line is centred
    assert project([(45.0, -93.0)]) == ([(MAP_W / 2, MAP_W / 2)], MAP_W) and project([]) == ([], MAP_W)
    east, h = project([(0.0, 0.0), (0.0, 1.0)])
    assert east[0][0] < east[1][0] and h == 30.0  # east is right; a flat line still gets a little height
    ctx = SimpleNamespace(config=SimpleNamespace(get=lambda key, default=None: default))
    ctx.waypoints = WaypointManager(ctx, data_dir=tmp_path)
    ctx.trips = TripManager(ctx, data_dir=tmp_path)
    a, b, c = (ctx.waypoints.add_waypoint(n, 45.0 + i / 100, -93.0 + i / 100) for i, n in enumerate(("Trailhead", "Falls", "Camp")))
    trip = ctx.trips.add_trip("e1", "Day one")
    assert route_map(ctx, "e1") is None
    for w in (a, c):
        ctx.trips.add_waypoint_to_route(trip.trip_id, w.waypoint_id)
    assert [p["name"] for p in route_map(ctx, "e1")["points"]] == ["Trailhead", "Camp"]  # planned, none logged
    for w in (a, b, c):
        ctx.trips.record_split(trip.trip_id, w.waypoint_id)
    drawn = route_map(ctx, "e1")
    assert [p["name"] for p in drawn["points"]] == ["Trailhead", "Falls", "Camp"] and drawn["w"] == MAP_W
    assert all(0 <= p["x"] <= MAP_W and 0 <= p["y"] <= drawn["h"] for p in drawn["points"])
