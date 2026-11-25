"""
tests.test_calendar_move
==========================

"Actually, make it Sunday" (core/calendar_move.py): the event his words name, else the newest, moved to a weekday,
"tomorrow" or an ISO date, a time kept unless he gives one; nothing to move, or no day, is said.
"""

from datetime import date
from types import SimpleNamespace

from core import calendar_move as cm


class _Calendar:
    """Two events, in the order added, and their updates."""

    def __init__(self):
        """The dentist first, the oil change last."""
        self.events = [SimpleNamespace(event_id="a", title="Dentist", date="2026-12-01", time="09:00"),
                       SimpleNamespace(event_id="b", title="Change the truck oil", date="2026-11-28", time=None)]

    def all_events(self):
        """In the order added."""
        return list(self.events)

    def update_event(self, event_id, **fields):
        """Applies the change."""
        event = next(e for e in self.events if e.event_id == event_id)
        for k, v in fields.items():
            setattr(event, k, v)
        return event


def test_the_newest_moves_to_the_day_said_and_a_named_one_by_its_title():
    """"Make it Sunday": the oil change to Sunday the 29th; "move the dentist to Friday": the dentist, its 9:00 kept."""
    cal = _Calendar()
    context = SimpleNamespace(calendar=cal)
    assert cm.move(context, "", "actually make it Sunday", "", date(2026, 11, 24)) == \
        "Moved 'Change the truck oil' to Sunday, November 29."
    assert cm.move(context, "the dentist", "Friday", "", date(2026, 11, 24)).startswith("Moved 'Dentist' to Friday")
    assert cal.events[0].time == "09:00"
    # a day he named wins over a date the model made up
    assert cm.day_of("Move it to Monday 2024-01-01", date(2026, 11, 24)) == "2026-11-30"


def test_nothing_to_move_or_no_day_is_said():
    """An empty calendar, or no day or time: asked."""
    assert cm.move(SimpleNamespace(calendar=SimpleNamespace(all_events=lambda: [])), "", "Sunday").startswith(
        "There's nothing on your calendar")
    assert cm.move(SimpleNamespace(calendar=_Calendar()), "", "whenever").startswith("To when?")



def test_an_events_day_passed_as_words_is_read_as_its_date():
    """"Friday at 2pm" is the coming Friday; an ISO date stays; nothing readable is None."""
    assert cm.event_day("2026-12-24") == "2026-12-24"
    assert cm.event_day("whenever") is None
    assert len(cm.event_day("Friday at 2pm") or "") == 10
