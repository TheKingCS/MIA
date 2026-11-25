"""
tests.test_weather_watch
==========================

The forecast read against his confirmed garden plans and his flock (core/weather_watch.py, brainstorm 2.2): frost
against tender crops in the ground, a hard freeze against half-hardy ones, a cold night against seedlings hardening
off, heat and freezing water against the hens, rain likely tomorrow (by its chance, else its words) against a build
in progress, a night cold enough for the pipes (said when asked, never as the daily message); in °F and °C;
through the gate once per concern per day; a gap in tomorrow's figures never loses today.
"""

from datetime import date, datetime
from types import SimpleNamespace

from core import weather_watch as ww


def _plan(crops, last_frost="April 20", status="confirmed", kind="garden"):
    return SimpleNamespace(kind=kind, status=status, last_frost=last_frost, crops=[{"crop": c} for c in crops])


def _forecast(low, high=60, unit="°F", tomorrow_high=None):
    return {"text": "x", "high": high, "low": low, "unit": unit,
            "tomorrow": {"high": tomorrow_high if tomorrow_high is not None else high, "low": low, "words": ""}}


def test_crops_are_in_the_ground_from_their_day_out_until_after_harvest():
    plans = [_plan(["tomato", "lettuce", "pea"])]
    early_may = ww.crops_now(plans, date(2026, 5, 2))  # tomatoes go out a week after April 20
    assert ("Tomatoes", "tender") in early_may["in_ground"]
    march = ww.crops_now(plans, date(2026, 3, 1))
    assert not any(n == "Tomatoes" for n, _ in march["in_ground"])
    assert ww.crops_now(plans, date(2026, 4, 20)) != {"in_ground": [], "hardening": []}


def test_seedlings_hardening_off_are_found_before_their_day_out():
    found = ww.crops_now([_plan(["tomato"])], date(2026, 4, 20))  # out April 27, hardening from April 17
    assert found["hardening"] == ["Tomatoes"] and found["in_ground"] == []


def test_drafts_and_builds_are_never_watched():
    assert ww.crops_now([_plan(["tomato"], status="draft"), _plan(["tomato"], kind="build")],
                        date(2026, 5, 10)) == {"in_ground": [], "hardening": []}


def test_frost_tonight_names_the_tender_crops_in_the_ground():
    growing = {"in_ground": [("Tomatoes", "tender"), ("Peppers", "tender"), ("Kale", "hardy")], "hardening": []}
    [frost] = ww.concerns(_forecast(33), growing, 0)
    assert frost["kind"] == "frost" and "tomatoes and peppers" in frost["text"] and "kale" not in frost["text"]
    assert ww.concerns(_forecast(40), growing, 0) == []


def test_a_hard_freeze_warns_for_half_hardy_crops_too():
    growing = {"in_ground": [("Tomatoes", "tender"), ("Lettuce", "half-hardy")], "hardening": []}
    kinds = [c["kind"] for c in ww.concerns(_forecast(27), growing, 0)]
    assert kinds == ["frost", "hard_freeze"]
    assert [c["kind"] for c in ww.concerns(_forecast(30), growing, 0)] == ["frost"]


def test_celsius_forecasts_use_the_same_thresholds():
    growing = {"in_ground": [("Tomatoes", "tender")], "hardening": []}
    assert [c["kind"] for c in ww.concerns(_forecast(1, high=10, unit="°C"), growing, 0)] == ["frost"]
    assert ww.concerns(_forecast(3, high=10, unit="°C"), growing, 0) == []
    assert "1°C" in ww.concerns(_forecast(1, high=10, unit="°C"), growing, 0)[0]["text"]


def test_a_cold_night_brings_hardening_seedlings_in():
    [c] = ww.concerns(_forecast(44), {"in_ground": [], "hardening": ["Tomatoes"]}, 0)
    assert c["kind"] == "hardening" and "tomatoes" in c["text"]


def test_the_flock_gets_heat_and_frozen_water_warnings_only_with_birds():
    assert [c["kind"] for c in ww.concerns(_forecast(70, high=92), {}, 6)] == ["flock_heat"]
    assert [c["kind"] for c in ww.concerns(_forecast(30, high=40), {}, 6)] == ["flock_water"]
    assert ww.concerns(_forecast(30, high=95), {}, 0) == []
    assert [c["kind"] for c in ww.concerns(_forecast(70, high=80, tomorrow_high=93), {}, 3)] == ["flock_heat"]


def test_no_forecast_means_nothing_to_say():
    assert ww.concerns({}, {"in_ground": [("Tomatoes", "tender")]}, 5) == []
    ctx = SimpleNamespace(project_plans=None, flock=None)
    assert ww.watch(ctx, forecast={"status": "PLANNED", "set": True, "text": None}) == []


def test_the_daily_message_goes_through_the_gate_once_per_concern_per_day():
    ctx = SimpleNamespace(project_plans=SimpleNamespace(listed=lambda: [_plan(["tomato"])]),
                          flock=SimpleNamespace(flocks=[SimpleNamespace(hens=4, roosters=0)]))
    import core.weather as weather

    original = weather.card
    weather.card = lambda context, fetch=None: _forecast(31, high=50)
    try:
        said = ww.offer(ctx, datetime(2026, 5, 3, 7, 0))
    finally:
        weather.card = original
    assert [c.title for c in said] == ["Frost tonight", "The hens' water may freeze"]
    assert all(c.topic == "weather_watch" and c.urgency == "timely" for c in said)
    assert said[0].fingerprint == "weather-frost-2026-05-03"
    assert said[0].expires.startswith("2026-05-04T09")


def test_say_tells_him_when_nothing_is_planted_or_kept(monkeypatch):
    import core.weather as weather

    monkeypatch.setattr(weather, "card", lambda context, fetch=None: dict(_forecast(31), place="Town"))
    monkeypatch.setattr(weather, "say", lambda context: "In Town it's x.")
    ctx = SimpleNamespace(project_plans=None, flock=None)
    assert "Nothing of yours is planted out" in ww.say(ctx)
    ctx = SimpleNamespace(project_plans=None, flock=SimpleNamespace(flocks=[SimpleNamespace(hens=2, roosters=0)]))
    assert "hens' water may freeze" in ww.say(ctx)


def test_rain_likely_tomorrow_is_said_to_a_build_in_progress():
    forecast = _forecast(50, high=60)
    forecast["tomorrow"]["rain"] = 80
    [rain] = ww.concerns(forecast, {}, 0, ("Chicken coop",))
    assert rain["kind"] == "rain_build" and "80% likely" in rain["text"] and "Chicken coop" in rain["text"]
    forecast["tomorrow"]["rain"] = 30
    assert ww.concerns(forecast, {}, 0, ("Chicken coop",)) == []
    forecast["tomorrow"]["rain"] = 90
    assert ww.concerns(forecast, {}, 0, ()) == []


def test_only_confirmed_builds_with_an_active_mission_count():
    plans = [SimpleNamespace(title="Coop", kind="build", status="confirmed", mission_ids=["m1"]),
             SimpleNamespace(title="Shed", kind="build", status="confirmed", mission_ids=["m2"]),
             SimpleNamespace(title="Deck", kind="build", status="draft", mission_ids=[]),
             SimpleNamespace(title="Beds", kind="garden", status="confirmed", mission_ids=["m1"])]
    missions = [SimpleNamespace(mission_id="m1", status="active"), SimpleNamespace(mission_id="m2", status="completed")]
    ctx = SimpleNamespace(project_plans=SimpleNamespace(listed=lambda: plans),
                          missions=SimpleNamespace(all_missions=lambda: missions))
    assert ww._builds(ctx) == ("Coop",)


def test_rain_in_tomorrows_words_counts_when_no_chance_is_given():
    forecast = _forecast(50, high=60)
    forecast["tomorrow"]["words"] = "Thunderstorm"
    [rain] = ww.concerns(forecast, {}, 0, ("Coop",))
    assert "says thunderstorm" in rain["text"]


def test_a_gap_in_tomorrows_figures_keeps_today():
    from core import weather

    raw = {"current": {"temperature_2m": 50, "weather_code": 0},
           "daily": {"time": ["d0", "d1"], "temperature_2m_max": [60, None], "temperature_2m_min": [40, None],
                     "weather_code": [0, 61]}}
    got = weather.read(raw, "fahrenheit")
    assert got["high"] == 60 and got["tomorrow"] is None



def test_a_night_cold_enough_for_the_pipes_is_said_when_asked_never_as_the_daily_message(monkeypatch):
    """A low of 15 °F: drip a faucet, open the cabinets, unhook hoses, heat at 55; the well's pump house with a well;
    -10 °C in Celsius; 25 °F says nothing of pipes; and the daily message leaves the pipes out."""
    from datetime import datetime

    cold = {"high": 28, "low": 18, "unit": "°F", "tomorrow": {"high": 25, "low": 15}}
    found = {c["kind"]: c["text"] for c in ww.concerns(cold, {"in_ground": [], "hardening": []}, 0, well=True)}
    assert "faucet on an outside wall drip" in found["pipes"] and "55°F" in found["pipes"]
    assert "pump house" in found["pipes"]
    metric = {"high": -4, "low": -8, "unit": "°C", "tomorrow": {"high": -5, "low": -10}}
    said = ww.concerns(metric, {"in_ground": [], "hardening": []}, 0)[0]["text"]
    assert "-7°C" in said and "13°C" in said and "pump house" not in said
    mild = {"high": 35, "low": 28, "unit": "°F", "tomorrow": {"high": 34, "low": 25}}
    assert not ww.concerns(mild, {"in_ground": [], "hardening": []}, 0)
    monkeypatch.setattr(ww, "watch", lambda context, day, fetch=None: [{"kind": "pipes", "text": "x"},
                                                                         {"kind": "frost", "text": "y"}])
    assert [c.message for c in ww.offer(None, datetime(2026, 12, 1, 7))] == ["y"]
