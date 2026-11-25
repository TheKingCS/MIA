"""
tests.test_daily_reminder
===========================

A reminder every day goes on the calendar (core/assistant_turn._daily_reminder_reply; the eleventh review: "remind
me every morning to give the dog his meds" had nowhere to go): a daily event from today, at the time said ("every
night at 9" is 21:00), undoable through add_calendar_event; the calendar repeats daily (core/calendar_manager:
CALENDAR_RECURRENCE_TYPES), while a bill or income never does.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn
from core.calendar_manager import CALENDAR_RECURRENCE_TYPES, RECURRENCE_TYPES, date_recurs_on


def test_a_daily_reminder_goes_on_the_calendar_at_its_time():
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append((n, a)) or "ok"))
    assistant_turn._daily_reminder_reply(context, "remind me every morning to give the dog his meds")
    assert ran[-1] == ("add_calendar_event", {"title": "Give the dog his meds", "date": date.today().isoformat(),
                                              "recurrence": "daily"})
    assistant_turn._daily_reminder_reply(context, "remind me every night at 9 to lock the coop")
    assert ran[-1][1]["time"] == "21:00" and ran[-1][1]["title"] == "Lock the coop"
    assistant_turn._daily_reminder_reply(context, "remind me every day at 7am to take my vitamins")
    assert ran[-1][1]["time"] == "07:00"
    for words in ("remind me why I get up every morning", "remind me to call mom tomorrow"):
        assert assistant_turn._daily_reminder_reply(context, words) is None, words


def test_the_calendar_repeats_daily_and_bills_never_do():
    assert "daily" in CALENDAR_RECURRENCE_TYPES and "daily" not in RECURRENCE_TYPES
    assert date_recurs_on(date(2026, 11, 25), "daily", date(2026, 12, 3))
    assert not date_recurs_on(date(2026, 11, 25), "daily", date(2026, 11, 24))
