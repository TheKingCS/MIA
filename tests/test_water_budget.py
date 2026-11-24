"""The whole property's water (core/water_budget.py): the house, garden, orchard and flock a day from his records
(each estimate said as one), the greenhouse said as not counted, tanks at their latest logged level, the days the
stored water carries the outdoor uses, the roof's catch from his logged rain, and the questions reaching the tools.
A propane or fish tank is never stored water, and a fish-tank question isn't the budget."""

from datetime import date
from types import SimpleNamespace

import pytest

from core import water_budget as wb
from core.data_logger_manager import DataLoggerManager


@pytest.fixture
def place(tmp_path):
    """Two people, a confirmed 100 sq ft garden, three fruit trees, eight hens, a data logger and a 600 sq ft roof."""
    settings = {"prepared.people": 2, "water.roof_sqft": 600}
    plan = SimpleNamespace(kind="garden", status="confirmed", beds=[{"length_ft": 10, "width_ft": 10}])
    assets = [SimpleNamespace(asset_id="a", name="3 Honeycrisp apple trees")]
    context = SimpleNamespace(
        config=SimpleNamespace(get=lambda k, d=None: settings.get(k, d)),
        project_plans=SimpleNamespace(listed=lambda: [plan]),
        maintenance=SimpleNamespace(all_assets=lambda: assets),
        flock=SimpleNamespace(flocks=[SimpleNamespace(hens=8)]),
        data_logger=DataLoggerManager(SimpleNamespace(config=None), data_dir=tmp_path))
    return context


def test_each_use_a_day_from_his_records(place, monkeypatch):
    from core import person_settings

    monkeypatch.setattr(person_settings, "get", lambda c, k, d=None: c.config.get(k, d))
    got = {u["use"]: u["gal_day"] for u in wb.uses(place)}
    assert got == {"the house": 160.0, "the garden": 8.9, "the orchard": 4.3, "the flock": 1.0}


def test_tanks_carry_the_outdoor_uses_and_the_roof_catches_his_rain(place, monkeypatch):
    from core import person_settings
    from core.weather_watch import RAIN_SERIES

    monkeypatch.setattr(person_settings, "get", lambda c, k, d=None: c.config.get(k, d))
    assert wb.log_level(place, "the Cistern", 1420) == "Logged: the cistern is at 1420 gallons."
    place.data_logger.add_reading(RAIN_SERIES, 2.0, timestamp="2026-11-20T08:00:00")
    said = wb.say(place, date(2026, 11, 24))
    assert "the cistern 1420 gallons" in said and "carries the garden, orchard and animals about 100 days" in said
    assert "roof caught about 598.1 gallons" in said and "greenhouse isn't counted" in said
    assert wb.log_level(place, "", 10) == "Which tank or cistern?"


def test_water_questions_reach_the_tools():
    from tests.assistant_registry import build_desktop_registry, demo_context

    registry = build_desktop_registry()
    context = SimpleNamespace(**vars(demo_context()), assistant_actions=registry)
    names = lambda said: [a.name for a in registry.matching_actions(said, context)]  # noqa: E731
    assert "water_budget" in names("how long will my water last?")
    assert registry.direct_lookup("How long will my water last?", context).name == "water_budget"  # in code
    assert "log_water_level" in names("the cistern is at 800 gallons")


def test_review_a_fuel_or_fish_tank_isnt_water_and_fish_questions_arent_the_budget(place):
    assert "isn't stored water" in wb.log_level(place, "propane tank", 40)
    assert wb.stored(place) == []
    from tests.assistant_registry import build_desktop_registry, demo_context

    registry = build_desktop_registry()
    context = SimpleNamespace(**vars(demo_context()), assistant_actions=registry)
    for said in ("is there enough water in the fish tank?", "the propane tank is at 40 percent"):
        assert {"water_budget", "log_water_level"}.isdisjoint(a.name for a in registry.matching_actions(said, context))
