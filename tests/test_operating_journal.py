"""The Operating Journal (DEC-0097, core/operating_journal.py): lines in the person's words, each read by code for
what the records can check; self-rated otherwise; how they did as plain numbers by week, never a judgment; talked
to with "add to my operating journal" and "rate ... 4"."""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from core import loops
from core import operating_journal as oj
from core.actions import ActionCenter
from core.life_events import LifeEvent

TODAY = date(2026, 11, 19)  # a Thursday
BY_ID = {l.id: l for l in loops.LOOPS}


def test_what_a_line_can_be_checked_against():
    assert oj.habit_from("Work out 4 times a week") == {"kind": "count", "type": "workout_logged", "per": "week",
                                                       "target": 4, "at_most": False, "area": "health", "word": "workouts"}
    assert oj.habit_from("cook at home five nights a week")["target"] == 5
    assert oj.habit_from("Call my mom once a week")["type"] == "caught_up"
    assert oj.habit_from("Spend no more than $200 on eating out a month") == {
        "kind": "spending", "category": "Eating Out", "per": "month", "target": 200.0, "at_most": True, "area": "money"}
    assert oj.habit_from("Be up before the sun")["kind"] == "self"
    assert oj.habit_from("I train every day")["target"] == 7


@pytest.fixture
def person(tmp_path, monkeypatch):
    from core import actions
    import core.life_events as le

    monkeypatch.setattr(actions, "_who", lambda context: "p1")
    journal = oj.OperatingJournal(None, tmp_path)
    history = []
    monkeypatch.setattr(le, "events_for", lambda context, since=None, until=None, types=None, ref=None: [
        e for e in history if (not types or e.type in types) and (not since or e.day >= since) and (not until or e.day <= until)])
    return SimpleNamespace(operating_journal=journal, actions=ActionCenter(), config=None, undo=None, history=history, events=None,
                           budget=None)


def workouts(person, per_week):
    monday = TODAY - timedelta(days=TODAY.weekday())
    for w, n in enumerate(per_week[::-1]):
        for i in range(n):
            day = monday - timedelta(weeks=w) + timedelta(days=i % 3)
            person.history.append(LifeEvent(f"w{w}-{i}", f"{day.isoformat()}T07:00:00", "workout_logged", "Workout"))


def test_how_they_did_in_plain_numbers(person):
    person.operating_journal.add("Work out 4 times a week")
    workouts(person, [4, 2, 5, 1])  # three full weeks, then this one so far
    m = oj.measure(person, person.operating_journal.lines[0], TODAY)
    assert m["values"] == [4, 2, 5, 1] and (m["on_pace"], m["of"]) == (2, 3)
    line = oj.picture(person, TODAY)[0]
    assert "4, 2, 5, 1 workouts by week" in line and "2 of 3 full weeks at 4 or more" in line
    assert not any(w in line.lower() for w in ("failed", "should", "only", "missed", "bad"))  # never a judgment


def test_self_rated_lines_and_the_loop(person):
    early = person.operating_journal.add("Be up before the sun")
    assert "not rated yet" in oj.picture(person, TODAY)[0]
    person.operating_journal.rate(early["id"], 5, TODAY - timedelta(weeks=1))
    person.operating_journal.rate(early["id"], 3, TODAY)
    m = oj.measure(person, early, TODAY)
    assert m["values"][-2:] == [5, 3] and m["on_pace"] == 1
    person.operating_journal.add("Work out 4 times a week")
    workouts(person, [4, 2, 5, 1])
    real = oj.pace
    import core.operating_journal as module

    module.pace = lambda context, today=None: real(context, TODAY)  # the loop measures on the test's day
    try:
        reading = BY_ID["journal.pace"].measure(person)
    finally:
        module.pace = real
    assert reading.n == 5 and "health 2/3" in reading.detail and BY_ID["journal.pace"].acts == "watch"


def test_talking_to_it(person):
    said = oj.reply(person, "add to my operating journal: cook at home 5 nights a week")
    assert "check it against your meals logged" in said and person.operating_journal.lines[0]["habit"]["target"] == 5
    oj.reply(person, "Add to my operating journal: be up before the sun")
    assert "Noted: 4 out of 5" in oj.reply(person, "rate up before the sun 4")
    assert oj.reply(person, "what's for dinner") is None


def test_the_sunday_question_only_for_lines_theirs_to_rate(person):
    sunday = date(2026, 11, 22)
    person.operating_journal.add("Work out 4 times a week")
    assert oj.weekly_offer(person, sunday) == []  # the records answer that one
    line = person.operating_journal.add("Be up before the sun")
    offer = oj.weekly_offer(person, sunday)
    assert offer[0].topic == "operating_journal" and "rate be up before 4" in offer[0].message
    person.operating_journal.rate(line["id"], 4, sunday)
    assert oj.weekly_offer(person, sunday) == [] and oj.weekly_offer(person, TODAY) == []
