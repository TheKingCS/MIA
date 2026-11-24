"""
tests.test_watering
=====================

"Should I water the garden today?" (core/weather_watch.watering): rain now or likely tomorrow says hold off, a hot dry
day says water deeply in the morning, the crops in the ground named, every answer ending with the soil check, no
forecast still giving the soil check; tomorrow's words read when there's no chance; freezing or snow says no watering;
nothing planted said; a middling chance never said as no rain.
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


def test_rain_said_only_in_tomorrows_words_still_holds_off():
    hot = {"high": 90, "unit": "°F", "words": "Clear", "tomorrow": {"words": "Heavy rain"}}
    assert "Tomorrow's forecast says heavy rain, so hold off" in ww.watering(hot, [("Tomatoes", True)])


def test_freezing_or_snow_says_no_watering_and_nothing_planted_is_said():
    assert ww.watering({"high": 25, "unit": "°F", "words": "Heavy snow", "tomorrow": {"rain": 0}}, []).startswith(
        "No watering today")
    assert ww.watering({"high": 70, "unit": "°F", "words": "Clear", "tomorrow": None}, []).startswith(
        "Nothing's planted out that I know of.")


def test_a_middling_chance_is_never_said_as_no_rain():
    said = ww.watering({"high": 70, "unit": "°F", "words": "Clear", "tomorrow": {"rain": 50}}, [("Kale", True)])
    assert "No rain" not in said and said.startswith("Only a 50% chance of rain tomorrow")
