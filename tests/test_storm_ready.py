"""
tests.test_storm_ready
========================

"Is a storm coming?" (core/storm_ready.py): stormy days found by their weather or gusts in the next three (a night
cold enough for the pipes adds them to the list), and a
checklist from his records; the forecast's gusts read when Open-Meteo gives them (core/weather.read).
"""

from types import SimpleNamespace

from core import storm_ready, weather


def test_the_forecast_keeps_each_days_strongest_gust():
    """Open-Meteo's wind_gusts_10m_max is each day's gust; a day without it has none."""
    raw = {"current": {"temperature_2m": 50, "weather_code": 3},
           "daily": {"time": ["2026-11-24", "2026-11-25"], "temperature_2m_max": [55, 48],
                     "temperature_2m_min": [40, 30], "weather_code": [3, 95], "wind_gusts_10m_max": [12, 47]}}
    got = weather.read(raw, "fahrenheit")
    assert got["days"][1]["gust"] == 47 and got["tomorrow"]["words"] == "Thunderstorms"
    assert "wind_gusts_10m_max" in weather.forecast_url(40.0, -90.0, "fahrenheit")


def test_storm_days_are_found_by_weather_or_wind_and_calm_days_arent():
    """Thunderstorms, freezing rain and a 45 mph gust count; a light rain at 20 mph doesn't; only three days."""
    forecast = {"unit": "°F", "days": [
        {"date": "2026-11-24", "words": "Light rain", "gust": 20},
        {"date": "2026-11-25", "words": "Thunderstorms", "gust": 30},
        {"date": "2026-11-26", "words": "Overcast", "gust": 45},
        {"date": "2026-11-27", "words": "Freezing rain", "gust": 10}]}
    found = storm_ready.storms(forecast)
    assert [s["date"] for s in found] == ["2026-11-25", "2026-11-26"]
    assert found[1]["why"] == "gusts to 45 mph"


def test_the_checklist_says_only_what_applies(monkeypatch):
    """No hens, greenhouse or builds: the generator, water, charging and the outage clock; with hens and the
    greenhouse taken over, their lines too."""
    from core import power_ready, weather_watch

    monkeypatch.setattr(power_ready, "say", lambda context: "Power: 3 days of generator fuel.")
    monkeypatch.setattr(weather_watch, "_builds", lambda context: ())
    monkeypatch.setattr(weather_watch, "_birds", lambda context: 0)
    context = SimpleNamespace(kitchen=None, config=None, greenhouse_link=None)
    lines = storm_ready.checklist(context)
    assert lines[0] == "Power: 3 days of generator fuel." and "Fill water jugs" in lines[1]
    assert not any("hens" in l or "greenhouse" in l for l in lines) and "the power went out" in lines[-1]
    monkeypatch.setattr(weather_watch, "_birds", lambda context: 6)
    context.greenhouse_link = SimpleNamespace(taken_over=True)
    lines = storm_ready.checklist(context)
    assert any("hens" in l for l in lines) and any("air pump" in l for l in lines)



def test_a_night_cold_enough_for_the_pipes_adds_them_to_the_storm_list(monkeypatch):
    """An ice storm with a 12 °F night: drip a faucet and the well's pump house; a 30 °F night adds nothing."""
    from core import weather_watch

    monkeypatch.setattr(weather_watch, "_well", lambda context: True)
    context = SimpleNamespace(kitchen=None, config=None, greenhouse_link=None)
    monkeypatch.setattr(weather_watch, "_birds", lambda context: 0)
    monkeypatch.setattr(weather_watch, "_builds", lambda context: ())
    from core import power_ready
    monkeypatch.setattr(power_ready, "say", lambda context: "Fuel: fine.")
    cold = {"unit": "°F", "days": [{"date": "2026-01-10", "low": 25}, {"date": "2026-01-11", "low": 12}]}
    lines = storm_ready.checklist(context, cold)
    pipes = [line for line in lines if "pipes" in line]
    assert pipes and "a low of 12°F" in pipes[0] and "pump house" in pipes[0]
    mild = {"unit": "°F", "days": [{"date": "2026-01-10", "low": 30}]}
    assert not [line for line in storm_ready.checklist(context, mild) if "pipes" in line]
