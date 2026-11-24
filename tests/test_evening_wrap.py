"""
tests.test_evening_wrap
=========================

The evening wrap (core/evening_wrap.py, DEC-0292): today's wins, tomorrow's first thing and its weather in two
sentences, from his hour on, once a day through the gate; nothing when there's nothing to say; an alarm is never
tomorrow's first thing, and one of a thing is said singular.
"""

from datetime import datetime
from types import SimpleNamespace

from core import evening_wrap as ew

NOW = datetime(2026, 11, 23, 20, 30)


def _parts(monkeypatch, done="2 workouts, 1 bills paid", first="Pay the power bill", sky="rain, 48°F and 35"):
    monkeypatch.setattr(ew, "done_today", lambda context, today: done)
    monkeypatch.setattr(ew, "first_tomorrow", lambda context, tomorrow: first)
    monkeypatch.setattr(ew, "weather_tomorrow", lambda context: sky)
    monkeypatch.setattr(ew, "_hour", lambda context: 20)


def test_the_wrap_is_two_sentences_from_his_records(monkeypatch):
    _parts(monkeypatch)
    assert ew.wrap(None, NOW) == ("Today: 2 workouts, 1 bills paid. Tomorrow, first up, Pay the power bill; the "
                                  "weather: rain, 48°F and 35.")


def test_a_quiet_day_says_so_and_nothing_at_all_says_nothing(monkeypatch):
    _parts(monkeypatch, done="", sky="")
    assert ew.wrap(None, NOW) == "A quiet day today. Tomorrow, first up, Pay the power bill."
    _parts(monkeypatch, done="", first="", sky="")
    assert ew.wrap(None, NOW) == "" and ew.offer(None, NOW) == []


def test_it_comes_from_his_hour_once_a_day(monkeypatch):
    _parts(monkeypatch)
    assert ew.offer(None, NOW.replace(hour=19)) == []
    [said] = ew.offer(None, NOW)
    assert said.topic == "evening_wrap" and said.urgency == "timely"
    assert said.fingerprint == "evening-wrap-2026-11-23" and said.expires == "2026-11-24T00:00:00"


def test_tomorrows_weather_comes_from_the_kept_forecast(monkeypatch):
    import core.weather as weather

    monkeypatch.setattr(weather, "card", lambda context, fetch=None: {
        "text": "50°F", "unit": "°F", "tomorrow": {"high": 48, "low": 35, "words": "Rain"}})
    assert ew.weather_tomorrow(SimpleNamespace()) == "rain, 48°F and 35"
    monkeypatch.setattr(weather, "card", lambda context, fetch=None: {"status": "PLANNED", "set": True, "text": None})
    assert ew.weather_tomorrow(SimpleNamespace()) == ""


def test_an_alarm_is_never_tomorrows_first_thing(monkeypatch):
    import core.today as today

    alarm = SimpleNamespace(when="today", title="Alarm", time="06:30", module_id="toolbox")
    meeting = SimpleNamespace(when="today", title="Meet the roofer", time="09:00", module_id="calendar")
    monkeypatch.setattr(today, "today_items", lambda context, day: [alarm, meeting])
    assert ew.first_tomorrow(None, NOW.date()) == "Meet the roofer at 09:00"


def test_one_of_a_thing_is_said_singular():
    assert ew._count(1, "bills paid") == "1 bill paid" and ew._count(2, "bills paid") == "2 bills paid"
    assert ew._count(1, "workouts") == "1 workout"
