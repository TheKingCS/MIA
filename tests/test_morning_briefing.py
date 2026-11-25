"""
tests.test_morning_briefing
=============================

The morning briefing he asks for (core/morning_briefing.py; brainstorm round 14): off until he asks, his words set
its hour (7 unless he says a morning hour), turn it off, or are asked again for an evening hour; the words are
today's weather and his day from his records; the daily check offers it from his hour, once, until noon. A
negation, a question or anything else every morning never sets it (the Fable review).
"""

from datetime import datetime
from types import SimpleNamespace

from core import morning_briefing as mb


def test_his_words_set_it_turn_it_off_or_ask_again():
    assert mb.asked("Every morning tell me the weather and my day") == ("on", 7)
    assert mb.asked("every morning at 6 give me my day") == ("on", 6)
    assert mb.asked("give me a morning briefing at 8am") == ("on", 8)
    assert mb.asked("every morning at 9pm brief me")[0] == "ask"
    assert mb.asked("stop the morning briefing") == ("off", None)
    for words in ("good morning MIA", "what's the weather tomorrow?", "I had a rough morning"):
        assert mb.asked(words) is None, words


def test_the_words_are_the_weather_and_his_day(monkeypatch):
    from core import today, weather

    monkeypatch.setattr(weather, "card", lambda context: {"text": "40°F", "high": 52, "low": 33, "unit": "°F",
                                                          "today_words": "Light rain"})
    item = SimpleNamespace(when="today", module_id="calendar", title="Vet", time="14:00")
    monkeypatch.setattr(today, "today_items", lambda context, day=None: [item])
    said = mb.briefing(SimpleNamespace(), datetime(2026, 11, 26, 7, 30))
    assert said == ("Good morning. Today: light rain, a high of 52°F and a low of 33°F. 1 thing on today's list, first "
                    "up Vet at 14:00.")


def test_it_comes_only_when_asked_from_his_hour_until_noon(monkeypatch):
    monkeypatch.setattr(mb, "briefing", lambda context, now: "Good morning.")
    monkeypatch.setattr(mb, "hour", lambda context: None)
    assert mb.offer(SimpleNamespace(), datetime(2026, 11, 26, 8, 0)) == []
    monkeypatch.setattr(mb, "hour", lambda context: 7)
    assert mb.offer(SimpleNamespace(), datetime(2026, 11, 26, 6, 59)) == []
    [message] = mb.offer(SimpleNamespace(), datetime(2026, 11, 26, 8, 0))
    assert message.topic == "morning_briefing" and message.expires.startswith("2026-11-26T12:00")
    assert mb.offer(SimpleNamespace(), datetime(2026, 11, 26, 13, 0)) == []


def test_a_negation_a_question_or_anything_else_every_morning_never_sets_it():
    for words in ("don't stop the morning briefing", "did you stop the morning briefing?",
                  "why did you turn off the morning report", "don't give me a morning briefing",
                  "give me my morning briefing", "Every morning my back hurts, tell me what to do",
                  "tell me a joke every morning", "Every morning at 6 give me the egg count"):
        assert mb.asked(words) is None, words
