"""
tests.test_garden_week
========================

This week in the garden (core/garden_week.py): his confirmed garden plans' steps in the next seven days, said once a
week through the gate, with their days; nothing said when nothing's due.
"""

from datetime import date, datetime
from types import SimpleNamespace

from core import garden_week as gw


def _ctx(crops=("tomato",), status="confirmed"):
    plan = SimpleNamespace(kind="garden", status=status, last_frost="April 20", first_frost="October 15",
                           crops=[{"crop": c} for c in crops])
    return SimpleNamespace(project_plans=SimpleNamespace(listed=lambda: [plan]))


def test_the_weeks_steps_come_with_their_days():
    # tomatoes start indoors 7 weeks before April 20, 2027: March 2
    items = gw.this_week(_ctx(), date(2027, 2, 27))
    assert items == [(date(2027, 3, 2), "Start tomatoes indoors")]
    assert gw.words(items, date(2027, 2, 27)) == "Start tomatoes indoors (Tuesday)"
    assert gw.words(items, date(2027, 3, 1)) == "Start tomatoes indoors (tomorrow)"


def test_it_is_said_once_a_week_and_only_when_something_is_due():
    [said] = gw.offer(_ctx(), datetime(2027, 2, 27, 8))
    assert said.topic == "garden_week" and said.urgency == "ambient" and said.fingerprint == "garden-week-2027-W08"
    assert gw.offer(_ctx(), datetime(2027, 1, 10, 8)) == []  # nothing falls in that week
    assert gw.offer(_ctx(status="draft"), datetime(2027, 2, 27, 8)) == []


def test_without_plans_she_says_how_to_get_dates():
    assert "Confirmed garden plans" in gw.say(SimpleNamespace(project_plans=None), date(2027, 2, 27))
