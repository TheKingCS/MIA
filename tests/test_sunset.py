"""
tests.test_sunset
===================

"What time is sunset?" is her sun and moon for his town (get_sun_moon_info, the weather conversation check
2026-11-26: the model had passed his town as a waypoint and got "I don't have a waypoint called ..."); a saved
waypoint's name is always the waypoint.
"""

from types import SimpleNamespace

from core import assistant_turn


def test_the_words_reach_the_sun():
    pattern = next(p for n, p, _w in assistant_turn._OWN_TOOLS if n == "get_sun_moon_info")
    for words in ("what time is sunset?", "when is sunrise?", "when does the sun go down?",
                  "how much daylight is left?"):
        assert pattern.match(words), words
    assert not pattern.match("what time is the sunset cruise?")
    assert not pattern.match("when is sunrise tomorrow?")  # today's only: the model's


def test_his_town_given_as_a_waypoint_is_his_town(monkeypatch):
    from core import weather
    from core.assistant_tools import AssistantTools

    monkeypatch.setattr(weather, "place", lambda c: {"name": "Springfield, Illinois", "lat": 39.8, "lon": -89.6})
    said = AssistantTools._action_get_sun_moon_info(SimpleNamespace(waypoints=SimpleNamespace(all_waypoints=lambda: [])),
                                                    {"waypoint_name": "Springfield, Illinois"})
    assert said.startswith("For Springfield, Illinois:")


def test_a_saved_waypoint_wins_over_the_town(monkeypatch):
    from core import weather
    from core.assistant_tools import AssistantTools

    monkeypatch.setattr(weather, "place", lambda c: {"name": "Springfield, Illinois", "lat": 39.8, "lon": -89.6})
    spot = SimpleNamespace(name="Springfield Lake trailhead", latitude=39.7, longitude=-89.5)
    context = SimpleNamespace(waypoints=SimpleNamespace(all_waypoints=lambda: [spot]))
    said = AssistantTools._action_get_sun_moon_info(context, {"waypoint_name": "Springfield Lake trailhead"})
    assert said.startswith("For 'Springfield Lake trailhead':")
    said = AssistantTools._action_get_sun_moon_info(context, {"waypoint_name": "Springfield"})
    assert said.startswith("For Springfield, Illinois:")
