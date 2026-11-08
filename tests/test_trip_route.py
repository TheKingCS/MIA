"""A trip's route and checkpoints on the web and by voice (core/trip_route.py, core/assistant_trip_route_actions.py):
stops from saved waypoints, "arrived" logged now, the legs walked, an out-and-back route, and undo."""

from datetime import datetime
from types import SimpleNamespace

import pytest

from core import actions
from core.actions import ActionCenter, ActionError
from core.assistant_trip_route_actions import _add_stop, _arrived, _route
from core.trip_manager import TripManager
from core.trip_route import duration_words, pace_words, reached_in_order, route_card
from core.waypoint_manager import WaypointManager


@pytest.fixture
def trail(tmp_path, monkeypatch):
    monkeypatch.setattr(actions, "_who", lambda context: "p1")
    ctx = SimpleNamespace(config=SimpleNamespace(get=lambda key, default=None: default), undo=None, events=None,
                          actions=ActionCenter())
    ctx.waypoints = WaypointManager(ctx, data_dir=tmp_path)
    ctx.trips = TripManager(ctx, data_dir=tmp_path)
    ctx.ramp = ctx.waypoints.add_waypoint("Boat ramp", 45.0, -93.0)
    ctx.island = ctx.waypoints.add_waypoint("Heron island", 45.02, -93.0)
    ctx.trip = ctx.trips.add_trip("x1", "Morning paddle")
    return ctx


def act(ctx, kind, **params):
    proposal = ctx.actions.propose(ctx, kind, params, proposed_by="person")
    return proposal, ctx.actions.approve(ctx, proposal.proposal_id)


def test_the_words_for_a_leg():
    assert [duration_words(h) for h in (0.75, 1.083, 3, 0)] == ["45 min", "1 h 05 min", "3 h", "0 min"]
    assert (pace_words(3.44), pace_words(None)) == ("3.4 km/h", "")


def test_an_out_and_back_route_is_reached_in_order():
    assert reached_in_order(["a", "b", "a"], ["a"]) == [True, False, False]
    assert reached_in_order(["a", "b", "a"], ["a", "b", "a"]) == [True, True, True]
    assert reached_in_order(["a", "b", "c"], ["a", "c"]) == [True, False, True]


def test_stops_added_on_the_page_then_arriving_logs_the_legs(trail):
    t = trail.trip.trip_id
    proposal, done = act(trail, "trip.route_add", trip_id=t, waypoint_id=trail.ramp.waypoint_id)
    assert proposal.summary == "Add Boat ramp to the Morning paddle route"
    act(trail, "trip.route_add", trip_id=t, waypoint_id=trail.island.waypoint_id)
    card = route_card(trail, trail.trips.get_trip(t))
    assert [s["name"] for s in card["stops"]] == ["Boat ramp", "Heron island"] and card["planned_km"] == 2.2
    assert card["next"]["name"] == "Boat ramp" and card["legs"] == []
    trail.trips.record_split(t, trail.ramp.waypoint_id, datetime(2026, 10, 25, 7, 10))
    trail.trips.record_split(t, trail.island.waypoint_id, datetime(2026, 10, 25, 7, 52))
    card = route_card(trail, trail.trips.get_trip(t))
    assert card["next"] is None and all(s["reached"] for s in card["stops"])
    assert card["legs"] == [{"from": "Boat ramp", "to": "Heron island", "km": 2.22, "took": "42 min", "pace": "3.2 km/h"}]
    proposal, done = act(trail, "trip.route_add", trip_id=t, waypoint_id=trail.ramp.waypoint_id)
    assert proposal.summary.endswith("again (on the way back)")
    card = route_card(trail, trail.trips.get_trip(t))
    assert card["next"]["name"] == "Boat ramp" and [s["reached"] for s in card["stops"]] == [True, True, False]
    assert act(trail, "trip.arrived", trip_id=t, waypoint_id=trail.ramp.waypoint_id)[1].result.startswith(
        "Arrived at Boat ramp: 2.2 km from Heron island in ")
    act(trail, "trip.route_remove", trip_id=t, waypoint_id=trail.island.waypoint_id)
    assert [s["name"] for s in route_card(trail, trail.trips.get_trip(t))["stops"]] == ["Boat ramp", "Boat ramp"]
    with pytest.raises(ActionError, match="isn't on the route"):
        trail.actions.propose(trail, "trip.route_remove", {"trip_id": t, "waypoint_id": "nope"})
    with pytest.raises(ActionError, match="Add it in Navigation"):
        trail.actions.propose(trail, "trip.arrived", {"trip_id": t, "waypoint_id": "nope"})


def test_by_voice_the_trip_underway_is_the_one_meant(trail):
    assert _arrived(trail, {"waypoint": "boat ramp"}) == "No trip is underway. Which trip is it?"
    assert _add_stop(trail, {"waypoint": "boat ramp", "trip": "morning paddle"}) == \
        "Boat ramp is stop 1 on the Morning paddle route."
    trail.trips.update_trip(trail.trip.trip_id, status="active")
    _add_stop(trail, {"waypoint": "heron island"})
    assert _arrived(trail, {"waypoint": "the boat ramp"}) == "Arrived at Boat ramp. The clock's running from here."
    assert _route(trail, {}) == "Morning paddle: Boat ramp (reached), Heron island, 2.2 km planned. Next: Heron island."
    assert _arrived(trail, {"waypoint": "the old dam"}).startswith("I don't have a waypoint called")
