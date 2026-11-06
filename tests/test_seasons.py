"""Seasons of memory (build plan step 10, core/seasons.py): a month or a year against the one before, worked out in
code from the person's history and memories, phrased by the model from the sheet; each closed month and year kept
once in their folder; no money lines for a child."""

from datetime import date
from types import SimpleNamespace

from core import seasons
from core.life_events import LifeEvent

TODAY = date(2026, 11, 20)


def ev(kind, day, summary="", **payload):
    return LifeEvent(f"{kind}-{day}-{summary}", f"{day}T10:00:00", kind, summary or kind, payload=payload)


def test_the_periods():
    assert seasons.periods("month", TODAY) == ((date(2026, 11, 1), TODAY), (date(2026, 10, 1), date(2026, 10, 20)),
                                               "November so far")
    assert seasons.periods("last month", TODAY)[0] == (date(2026, 10, 1), date(2026, 10, 31))
    assert seasons.periods("year", date(2028, 2, 29))[1][1] == date(2027, 2, 28)
    assert seasons.periods("last year", TODAY)[2] == "2025"
    assert seasons.kind_in("How did October go?", TODAY) == "last month"
    assert seasons.kind_in("How was my year?", TODAY) == "year" and seasons.kind_in("what about 2025", TODAY) == "last year"
    assert seasons.kind_in("What changed this month?", TODAY) == "month"


def test_what_changed_between_two_periods():
    now = [ev("workout_logged", "2026-11-03", minutes=40)] * 6 + [ev("eggs_collected", "2026-11-04", eggs=12),
           ev("expense_added", "2026-11-05", amount=80), ev("bill_paid", "2026-11-05", "Paid the power bill", amount=120),
           ev("income_received", "2026-11-06", amount=2000), ev("harvest", "2026-11-07", "Harvested the squash")]
    before = [ev("workout_logged", "2026-10-03", minutes=40)] * 3 + [ev("meal_logged", "2026-10-04")] * 4 + \
             [ev("bill_paid", "2026-10-05", amount=120)]
    lines = seasons.compare(now, before, "November so far", memories_now={"Family": 2, "Fitness": 1})
    text = " ".join(lines)
    assert "More in November so far: workouts 6, up from 3" in text
    assert "New in November so far:" in text and "eggs collected (1)" in text and "harvests (1)" in text
    assert "Stopped in November so far: meals logged (none, after 4 the period before)." in text
    assert "Minutes trained: 240 in November so far, 120 the period before." in text
    assert "2,000.00 in and 200.00 out" in text and "2 about family, 1 about fitness" in text
    assert "Harvested the squash" in text


def test_a_child_sees_no_money_and_undone_things_dont_count():
    now = [ev("bill_paid", "2026-11-05", amount=120), ev("task_done", "2026-11-06")]
    undo = LifeEvent("u1", "2026-11-06T11:00:00", "undone", "Undid", payload={"reverses": [now[1].event_id]})
    lines = seasons.compare(now + [undo], [], "November so far", money=False)
    assert not any("Money" in l or "bills" in l for l in lines) and not any("tasks" in l for l in lines)


def test_closed_months_are_kept_once(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(seasons, "season", lambda context, kind, today=None: calls.append(kind) or (kind, [f"{kind} line"]))
    person = SimpleNamespace(failures=SimpleNamespace(data_dir=tmp_path))
    assert seasons.close_past(person, TODAY) == ["2026-10", "2025"]
    assert seasons.close_past(person, TODAY) == []  # once each
    assert seasons.kept(person)["2026-10"]["lines"] == ["last month line"] and calls == ["last month", "last year"]
