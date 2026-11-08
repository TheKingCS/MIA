"""
tests.test_web_comms
======================

Communications (DEC-0129, core/web_comms.py): people to catch up with (longest first, only those you can write to),
and the message limit and breaks as undoable actions on the real communication gate.
"""

from datetime import date
from types import SimpleNamespace

import pytest

from core.actions import ACTION_TYPES, ActionError
from core.web_comms import catch_up


def test_people_you_can_write_to_longest_since_first():
    people = [SimpleNamespace(person_id="a", name="Alex", email="a@x.org", last_contact="2026-11-01"),
              SimpleNamespace(person_id="j", name="Jordan", email="j@x.org", last_contact="2026-09-28"),
              SimpleNamespace(person_id="s", name="Sam", email="s@x.org", last_contact=""),
              SimpleNamespace(person_id="n", name="No Email", email="", last_contact="2026-01-01")]
    rows = catch_up(people, date(2026, 11, 8))
    assert [(r["name"], r["since"]) for r in rows] == [("Sam", None), ("Jordan", 41), ("Alex", 7)]


class _Gate:
    """A stand-in gate keeping a limit and one kind of message on a break."""

    def __init__(self):
        """Limit 5; news digests on a break."""
        self.budget, self.breaks = 5, [{"topic": "news_digest", "label": "news digests"}]

    def set_daily_budget(self, n):
        """Clamps like the real gate (at least 1)."""
        self.budget = max(1, n)
        return self.budget

    def paused(self):
        """The kinds on a break."""
        return list(self.breaks)

    def resume(self, topic):
        """Ends a break."""
        self.breaks = [b for b in self.breaks if b["topic"] != topic]


def test_the_limit_and_bringing_a_kind_back():
    context = SimpleNamespace(communication=_Gate())
    assert "At most 3 times" in ACTION_TYPES["comms.limit"].execute(context, {"count": "3"})
    assert context.communication.budget == 3
    assert "news digests again" in ACTION_TYPES["comms.resume"].execute(context, {"topic": "news_digest"})
    with pytest.raises(ActionError):
        ACTION_TYPES["comms.resume"].execute(context, {"topic": "news_digest"})
    with pytest.raises(ActionError):
        ACTION_TYPES["comms.limit"].execute(SimpleNamespace(), {"count": "3"})
