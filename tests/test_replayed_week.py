"""Tests for LS-09, a replayed week (core/replay.py): on a frozen clock, each day's due things are said on their day,
nothing twice, and a stop-everything holds her unprompted messages until it lifts."""
from datetime import datetime

import pytest

from core import communication_gate, replay, stop
from core.app_context import AppContext
from core.background_jobs import BackgroundJobs
from core.calendar_manager import CalendarManager
from core.communication_gate import CommunicationGate
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.notification_manager import NotificationManager

MONDAY = datetime(2026, 11, 23, 9, 0)


@pytest.fixture
def week(tmp_path, monkeypatch):
    """A person's MIA with a calendar, notifications and the gate in a temporary folder, and two events this week."""
    import core.config_manager as config_manager_module

    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(stop, "_mark_on_disk", lambda value: None)  # the real hold file is the PC's, not a test's
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.notifications = NotificationManager(context, data_dir=tmp_path)
    context.calendar = CalendarManager(context, data_dir=tmp_path)
    context.communication = CommunicationGate(context, data_dir=tmp_path)
    context.calendar.add_event("Dentist", "2026-11-24")  # Tuesday
    context.calendar.add_event("Feed store order", "2026-11-26")  # Thursday
    context.calendar.add_event("Barn raising", "2026-11-28")  # Saturday
    return context


def _days_saying(week_said, words):
    """The days whose messages mention `words`."""
    return [d["day"] for d in week_said if any(words in line for line in d["said"])]


def test_each_event_is_said_on_its_day_and_nothing_twice(week):
    """Tuesday's and Thursday's and Saturday's events each come once, on their own day."""
    said = replay.replay(week, BackgroundJobs(week), MONDAY)
    assert [d["day"] for d in said] == [f"2026-11-{n}" for n in range(23, 30)]
    assert _days_saying(said, "Dentist") == ["2026-11-24"]
    assert _days_saying(said, "Feed store order") == ["2026-11-26"]
    assert _days_saying(said, "Barn raising") == ["2026-11-28"]


def test_a_stop_holds_her_own_suggestions_but_never_his_reminders(week):
    """Stopped Wednesday until Friday: her own suggestion offered Wednesday waits and comes once after the stop lifts;
    Thursday's calendar (a reminder he set, core/stop.TOPICS_NEVER_HELD) still comes on its day."""
    from core.communication_gate import Candidate

    def before(day):
        """Wednesday morning he says stop everything until Friday, and she has a suggestion of her own."""
        if day.isoformat() == "2026-11-25":
            stop.stop_everything(week, until=datetime(2026, 11, 27, 0, 0), now=datetime(2026, 11, 25, 8, 0))
            week.communication.offer(Candidate("smart_suggestion", "An idea", "Sort the seed packets by month"),
                                     now=datetime(2026, 11, 25, 8, 30))

    said = replay.replay(week, BackgroundJobs(week), MONDAY, before_each=before)
    held = _days_saying(said, "Sort the seed packets")
    assert held and held[0] >= "2026-11-27" and len(held) == 1  # after the stop, once
    assert _days_saying(said, "Feed store order") == ["2026-11-26"]  # his reminder, never held
    assert _days_saying(said, "Barn raising") == ["2026-11-28"]
