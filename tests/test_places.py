"""
Location quests (DEC-0028 #13): places with what arriving does; the phone
only gets them when the person switched noticing on; arriving records it
and clears the map's fog there.
"""

import pytest

from core.actions import ActionCenter, ActionError
from core.places import Places, arrival, distance_m, places_page, watched
from core.world_map import WorldMap
from tests.engine_world import build_world


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.places = Places(context, data_dir=context.my_dir)
    context.world_map = WorldMap(context, data_dir=context.my_dir)
    return context


def do(world, kind, **params):
    proposal = world.actions.propose(world, kind, params)
    done = world.actions.approve(world, proposal.proposal_id)
    assert done.status == "executed", done.result
    return proposal, done


def test_distance():
    assert 105 < distance_m(40.0, -105.0, 40.001, -105.0) < 117


def test_add_watch_and_arrive(world):
    prop, _ = do(world, "place.add", name="Gym", lat=40.0, lon=-105.0, on_arrive="Start My Workout")
    assert "within 150 m" in prop.summary and "start my workout" in prop.summary
    with pytest.raises(ActionError):
        world.actions.propose(world, "place.add", {"name": "Bad", "lat": 40, "lon": -105, "on_arrive": "Fly"})
    with pytest.raises(ActionError):
        world.actions.propose(world, "place.add", {"name": "Huge", "lat": 40, "lon": -105, "radius": 9000})
    assert watched(world) == []  # off until the person switches it on
    from core import person_settings

    person_settings.put(world, "places.watch", True)
    [place] = watched(world)
    assert place["open"] == "workout.html#today" and place["say"].startswith("📍 You're at Gym.")
    _, done = do(world, "place.arrive", place_id=place["id"])
    assert "workout" in done.result
    page = places_page(world)
    assert page["watching"] and page["places"][0]["arrivals"] == 1
    assert world.world_map.checkins[0].label == "Gym"  # the fog cleared there too
    do(world, "place.delete", place_id=place["id"])
    assert world.places.places == []


def test_just_remind_me():
    from core.places import Place

    a = arrival(Place("x", "Library", 0, 0, note="Return the books"))
    assert a == {"say": "📍 You're at Library. Return the books", "open": "", "label": "OK"}
