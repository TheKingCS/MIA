"""Water off a roof (core/rain_catchment.py): a roof's square feet read from words, gallons an inch kept after
gutters and the first flush, what his logged rain would have caught, his beds' monthly need (4.33 weeks) set
against it, and the question reaching the tool."""

from datetime import date
from types import SimpleNamespace

import pytest

from core import rain_catchment as rc

TODAY = date(2026, 11, 24)


@pytest.mark.parametrize("said, sqft", [("400 square feet", 400), ("12 by 20", 240), ("12x20 ft", 240),
                                        ("300 sq ft", 300), ("250", 250), ("big", None)])
def test_a_roofs_size_is_read_from_how_he_says_it(said, sqft):
    assert rc.roof_sqft(said) == sqft


def test_gallons_an_inch_and_his_logged_rain_and_his_beds_month(tmp_path):
    from core.data_logger_manager import DataLoggerManager
    from core.weather_watch import RAIN_SERIES

    context = SimpleNamespace(data_logger=None)
    said = rc.say(context, "400 square feet", today=TODAY)
    assert "about 199.4 gallons from each inch" in said and "nothing logged in the last 30 days" in said
    logger = DataLoggerManager(SimpleNamespace(config=None), data_dir=tmp_path)
    logger.add_reading(RAIN_SERIES, 1.5, timestamp="2026-11-10T08:00:00")
    logger.add_reading(RAIN_SERIES, 0.5, timestamp="2026-09-01T08:00:00")  # too long ago
    said = rc.say(SimpleNamespace(data_logger=logger), "400 square feet", beds_sqft=100, today=TODAY)
    assert "logged 1.5 inches in the last 30 days" in said and "about 299 gallons" in said
    assert "100 square feet of beds take about 270 gallons a month" in said  # 4.33 weeks a month


def test_asking_about_rain_off_a_roof_reaches_it():
    from tests.assistant_registry import build_desktop_registry, demo_context

    registry = build_desktop_registry()
    context = SimpleNamespace(**vars(demo_context()), assistant_actions=registry)
    for said in ("how much rain could I catch off a 400 square foot roof?", "is rain catchment worth it on the shed"):
        assert "rain_catchment" in [a.name for a in registry.matching_actions(said, context)], said
