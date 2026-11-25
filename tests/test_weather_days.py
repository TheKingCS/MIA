"""
tests.test_weather_days
=========================

"What's the weather Saturday?" (core/weather.py `days_meant`, `say_days`): a weekday, the weekend, the day after
tomorrow and this week read from his words (a follow-up's own words first), each day said from the week's forecast,
and a day past it said as that.
"""

from datetime import date

from core import weather


def test_the_days_his_words_name():
    """From Tuesday 2026-11-24: Saturday is the 28th, the weekend the 28th and 29th, the day after tomorrow the 26th;
    a follow-up's own words win over the question it follows; no day named is None."""
    today = date(2026, 11, 24)
    assert weather.days_meant("what's the weather Saturday?", today) == [date(2026, 11, 28)]
    assert weather.days_meant("this weekend", today) == [date(2026, 11, 28), date(2026, 11, 29)]
    assert weather.days_meant("And the day after? (after: What's the weather tomorrow?)", today) == [date(2026, 11, 26)]
    assert weather.days_meant("tuesday", today) == [today] and len(weather.days_meant("this week", today)) == 7
    assert weather.days_meant("what's the weather?", today) is None


def test_each_day_said_from_the_forecast_and_past_it_said_as_that(monkeypatch):
    """Saturday with its rain and gusts; a day past the forecast: that it doesn't reach."""
    got = {"place": "Springfield", "unit": "°F", "text": "x", "days": [
        {"date": "2026-11-28", "high": 54, "low": 39, "words": "Light rain", "rain": 60, "gust": 30}]}
    monkeypatch.setattr(weather, "card", lambda context, fetch=None: got)
    said = weather.say_days(None, "what about Saturday?", date(2026, 11, 24))
    assert said == "In Springfield: Saturday: light rain, 54 and 39°F, a 60% chance of rain, gusts to 30 mph."
    assert "doesn't reach that far" in weather.say_days(None, "next Monday", date(2026, 11, 24))
