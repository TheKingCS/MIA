"""The homestead's power (core/power_picture.py): the essentials a day (his own, else typical and said so), the
battery's hours on them, his solar's last 30 days in kWh against them, the generator's line, a load he says kept or
taken off, and the questions reaching the tools; and the project picture reading this, never the computer's battery."""

from datetime import date
from types import SimpleNamespace

import pytest

from core import power_picture as pp


@pytest.fixture
def home(monkeypatch):
    """Settings he can say, a 10 kWh battery, and solar readings of 12 kWh a day."""
    from core import person_settings

    settings = {"power.battery_kwh": 10}
    monkeypatch.setattr(person_settings, "get", lambda c, k, d=None: settings.get(k, d))
    monkeypatch.setattr(person_settings, "put", lambda c, k, v: settings.__setitem__(k, v))
    reading = lambda day: SimpleNamespace(timestamp=f"2026-11-{day:02d}T18:00:00", value=12.0, unit="kWh")  # noqa: E731
    energy = SimpleNamespace(
        all_energy_sources=lambda: [SimpleNamespace(source_id="s", source_type="Solar")],
        energy_source_meter_names=lambda sid: ["daily kwh"],
        energy_source_readings=lambda sid, meter: [reading(20), reading(21)])
    return SimpleNamespace(config=SimpleNamespace(), energy=energy, settings=settings)


def test_typical_essentials_are_said_as_typical_and_his_own_replace_them(home):
    rows, mine = pp.loads(home)
    assert not mine and sum(r["kwh_day"] for r in rows) == pytest.approx(10.66)
    assert pp.set_load(home, "Well pump", 1200, 1) == "Kept: the well pump draws 1200 watts for 1 hours a day (1.2 kWh)."
    rows, mine = pp.loads(home)
    assert mine and [r["name"] for r in rows] == ["well pump"]
    assert pp.set_load(home, "well pump", 0, 1) == "Took the well pump off your essentials."


def test_the_battery_and_solar_against_the_essentials(home):
    said = pp.say(home, date(2026, 11, 24))
    assert "Typical essentials" in said and "about 10.66 kWh a day" in said
    assert "10 kWh battery carries them about 23 hours" in said
    assert "solar averaged 12 kWh a day" in said and "more than the essentials take" in said


def test_power_questions_reach_the_homesteads_picture_not_the_computers_battery():
    from tests.assistant_registry import build_desktop_registry, demo_context

    registry = build_desktop_registry()
    context = SimpleNamespace(**vars(demo_context()), assistant_actions=registry)
    names = lambda said: [a.name for a in registry.matching_actions(said, context)]  # noqa: E731
    assert "power_picture" in names("how long will my battery last if the power goes out?")
    assert "set_power_load" in names("the well pump draws 1000 watts for an hour a day")
