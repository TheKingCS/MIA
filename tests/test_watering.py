"""
tests.test_watering
=====================

"Should I water the garden today?" (core/weather_watch.watering): rain now or likely tomorrow says hold off, a hot dry
day says water deeply in the morning, the crops in the ground named, every answer ending with the soil check, and no
forecast still giving the soil check.
"""

from core import weather_watch as ww

SOIL = "Push a finger in 1 to 2 inches"


def test_rain_now_or_likely_tomorrow_says_hold_off():
    wet = {"high": 70, "unit": "°F", "words": "Light rain", "tomorrow": {"rain": 10}}
    assert "skip watering" in ww.watering(wet, []) and SOIL in ww.watering(wet, [])
    coming = {"high": 75, "unit": "°F", "words": "Clear", "tomorrow": {"rain": 80}}
    assert "80% likely tomorrow, so hold off for the tomatoes" in ww.watering(coming, [("Tomatoes", True)])


def test_a_hot_dry_day_says_water_deeply_in_the_morning():
    hot = {"high": 92, "unit": "°F", "words": "Clear", "tomorrow": {"rain": 5}}
    assert "water for the tomatoes and peppers deeply, early in the morning" in ww.watering(
        hot, [("Tomatoes", True), ("Peppers", True)])
    assert "hot" in ww.watering({"high": 31, "unit": "°C", "words": "Clear", "tomorrow": {}}, [])


def test_no_forecast_still_gives_the_soil_check():
    assert ww.watering({}, []).startswith("I don't have today's forecast. " + SOIL)
