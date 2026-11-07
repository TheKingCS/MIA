"""Recreation in the health cluster (DEC-0098, core/recreation.py): games and sports logged by voice or on a screen,
counted as training load (minutes × effort), skill XP by the sport, a life event for the history, the seasons, the
Operating Journal and the Chronicle; never mistaking a song for a game; each effort in a word for the screen."""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from core import loops, recreation
from core.actions import ActionCenter

BY_ID = {l.id: l for l in loops.LOOPS}


def test_what_was_said():
    assert recreation.parse("played pickleball for an hour with Sam and Jo, it was hard") == {
        "what": "pickleball", "minutes": 60, "effort": 7, "with": ["Sam", "Jo"], "date": date.today().isoformat()}
    hike = recreation.parse("went hiking for 2 hours yesterday, it was a 7 out of 10")
    assert (hike["minutes"], hike["effort"], hike["date"]) == (120, 7, (date.today() - timedelta(days=1)).isoformat())
    assert recreation.parse("played chess with my son")["with"] == ["my son"]
    for not_a_game in ("played that song again", "played guitar for an hour", "went to the store", "played a video game"):
        assert recreation.parse(not_a_game) is None, not_a_game
    assert recreation.skills_for("pickleball") == ("coordination", "athleticism")
    assert recreation.skills_for("chess") == ("athleticism",) and recreation.effort_of("brutal") == 9


@pytest.fixture
def person(tmp_path, monkeypatch):
    from core import actions

    monkeypatch.setattr(actions, "_who", lambda context: "p1")
    log = recreation.RecreationLog(None, tmp_path)
    return SimpleNamespace(recreation=log, actions=ActionCenter(), config=None, undo=None, events=None, workout=None)


def test_a_game_is_a_load_and_a_life_event(person, tmp_path):
    from core.life_events import LifeEventLog

    entry = person.recreation.log("pickleball", 60, "hard", ["Sam"])
    assert entry["load"] == 420 and entry["effort"] == 7 and entry["effort_said"]
    [event] = LifeEventLog(None, tmp_path).all_events()
    assert event.type == "played" and event.payload["load"] == 420 and "with Sam" in event.summary


def test_logging_by_voice(person):
    from core.quick_commands import _played

    said = _played(person, "played basketball for 45 minutes")
    assert "Logged basketball, 45 min: training load 225." in said and "How hard was it" in said
    assert _played(person, "played that song again") is None


def test_training_load_by_week_and_the_jump(person):
    today = date(2026, 11, 19)
    monday = today - timedelta(days=today.weekday())
    for w in range(1, 5):
        person.recreation.log("tennis", 60, 5, day=(monday - timedelta(weeks=w)).isoformat())
    person.recreation.log("tennis", 120, 8, day=monday.isoformat())
    weeks = recreation.load(person, today)
    assert [w["play_load"] for w in weeks] == [300, 300, 300, 300, 960]
    assert recreation.acute_chronic(weeks) == 3.2
    lines = recreation.lines(person, today)
    assert "Play load by week: 300, 300, 300, 300, 960" in lines[1] and "past 1.5" in lines[2]
    real = recreation.load
    recreation.load = lambda context, today_=None, weeks=5: real(context, today)
    try:
        reading = BY_ID["recreation.load"].measure(person)
    finally:
        recreation.load = real
    assert reading.value == 3.2 and loops.judge(BY_ID["recreation.load"], reading, [])["state"] == "below"
    assert BY_ID["recreation.load"].acts == "watch"  # theirs to see, never a task about their body


def test_it_counts_in_the_chronicle_and_the_journal():
    from core.chronicle import TYPE_THREAD
    from core.operating_journal import habit_from

    assert TYPE_THREAD["played"] == "play"
    assert habit_from("Play pickleball twice a week")["type"] == "played"


def test_an_effort_reads_as_a_word():
    from core.recreation import effort_word

    assert [effort_word(e) for e in (2, 3, 5, 6, 7, 10, None)] == ["Easy", "Easy", "Moderate", "Moderate", "Hard", "Hard", "Moderate"]
