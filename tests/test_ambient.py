"""MIA's ambient view for the second monitor, flowing to one monitor when the other goes (core/ambient.py,
gui/ambient_screens.py, DEC-0231, Zac's Q-80)."""

import json
from pathlib import Path

from core import ambient

SCHEMA = Path(__file__).resolve().parent.parent / "docs" / "schema"


def test_with_two_monitors_the_ambient_view_takes_the_one_the_window_is_not_on():
    from gui.ambient_screens import ambient_target

    assert ambient_target(["DISPLAY1", "DISPLAY2"], "DISPLAY1") == "DISPLAY2"
    assert ambient_target(["DISPLAY1", "DISPLAY2"], "DISPLAY2") == "DISPLAY1"


def test_with_one_monitor_there_is_no_ambient_window():
    from gui.ambient_screens import ambient_target

    assert ambient_target(["DISPLAY1"], "DISPLAY1") is None and ambient_target([], None) is None


def test_with_three_monitors_it_takes_the_first_other_one():
    from gui.ambient_screens import ambient_target

    assert ambient_target(["A", "B", "C"], "B") == "A"


def test_the_ambient_page_address_keeps_the_token_out_of_the_query():
    from gui.ambient_screens import ambient_url

    url = ambient_url("http://127.0.0.1:8765", "secret", 1.25, True)
    assert url.startswith("http://127.0.0.1:8765/web/ambient.html?") and url.endswith("#token=secret")
    assert "secret" not in url.split("#")[0] and "scale=1.25" in url and "contrast=high" in url


def test_the_ambient_view_is_homes_own_data_cut_to_what_can_be_glanced():
    home = {"date": "Tue, Nov 17", "weather": {"place": "Town", "text": "40°F, clear"},
            "focus": [{"title": f"Task {i}", "kind": "Today", "time": "9:00"} for i in range(6)],
            "upcoming": [{"title": "Dentist", "kind": "Soon"}],
            "life": {"music": {"title": "Song", "artist": "Band", "playing": True}},
            "mission": {"name": "Coop", "next": "Walls", "done": 2, "total": 5},
            "activity": {"running": [{"what": "Ordering seeds", "status": "running"}], "mine": [{"what": "Logged oil"}]}}
    v = ambient.shape(home)
    assert len(v["due"]) == ambient.DUE_SHOWN and v["due"][0] == {"title": "Task 0", "when": "Today", "time": "9:00"}
    assert v["next"]["title"] == "Dentist" and v["music"]["title"] == "Song" and v["mission"]["total"] == 5
    assert [a["what"] for a in v["activity"]] == ["Ordering seeds", "Logged oil"]


def test_parts_that_are_missing_stay_empty_instead_of_guessed():
    v = ambient.shape({})
    assert v == {"date": "", "weather": None, "due": [], "next": None, "music": None, "mission": None,
                 "activity": [], "briefing": ""}


def test_a_weather_card_still_loading_is_left_out():
    assert ambient.shape({"weather": {"status": "REAL", "loading": True, "text": None}})["weather"] is None


def test_the_demo_example_is_the_dashboard_example_shaped():
    home = json.loads((SCHEMA / "dashboard.example.json").read_text(encoding="utf-8"))
    assert json.loads((SCHEMA / "ambient.example.json").read_text(encoding="utf-8")) == ambient.shape(home)


def test_a_view_that_cannot_be_assembled_shows_the_clock_alone(monkeypatch):
    def broken(*_a, **_k):
        """A Home that fails."""
        raise RuntimeError("no stores")

    monkeypatch.setattr("core.web_surfaces.dashboard", broken)
    assert ambient.view(None)["due"] == []


def test_the_ambient_window_is_wanted_unless_turned_off():
    from types import SimpleNamespace

    from gui.ambient_screens import AmbientScreens

    on = AmbientScreens(SimpleNamespace(config=SimpleNamespace(get=lambda k, d=None: d)), None)
    off = AmbientScreens(SimpleNamespace(config=SimpleNamespace(get=lambda k, d=None: False)), None)
    assert on.enabled() and not off.enabled()
