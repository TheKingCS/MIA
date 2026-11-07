"""Waypoints from the web (core/waypoint_actions.py): added from a tap on the map, taken out from Navigation."""

from types import SimpleNamespace

import pytest

from core import actions
from core.actions import ActionCenter, ActionError
from core.waypoint_manager import WaypointManager


@pytest.fixture
def person(tmp_path, monkeypatch):
    monkeypatch.setattr(actions, "_who", lambda context: "p1")
    ctx = SimpleNamespace(config=None, undo=None, events=None, actions=ActionCenter())
    ctx.waypoints = WaypointManager(ctx, data_dir=tmp_path)
    return ctx


def act(ctx, kind, **params):
    return ctx.actions.approve(ctx, ctx.actions.propose(ctx, kind, params, proposed_by="person").proposal_id).result


def test_a_waypoint_added_where_the_map_was_tapped_and_taken_out(person):
    assert act(person, "waypoint.add", name=" Spring ", lat="40.010001", lon="-105.000002", category="nope") == "Added Spring."
    [w] = person.waypoints.all_waypoints()
    assert (w.latitude, w.longitude, w.category) == (40.010001, -105.000002, "")  # an unknown kind: none
    assert act(person, "waypoint.delete", waypoint_id=w.waypoint_id) == "Took Spring out."
    assert person.waypoints.all_waypoints() == []


@pytest.mark.parametrize("params", [{"name": "X", "lat": "abc", "lon": "1"}, {"name": "X", "lat": "91", "lon": "0"},
                                    {"name": " ", "lat": "1", "lon": "1"}])
def test_what_it_refuses(person, params):
    with pytest.raises(ActionError):
        person.actions.propose(person, "waypoint.add", params, proposed_by="person")
