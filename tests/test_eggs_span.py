"""
tests.test_eggs_span
======================

"How many eggs last week?" (core/assistant_goods_actions.py get_eggs): last week, this month and last month read from
his words (a follow-up's own first) and counted from the flock's log, both ends counted.
"""

from datetime import date, timedelta
from types import SimpleNamespace

from core import assistant_goods_actions as ga


def test_the_span_and_the_count():
    """Last week is 7 to 13 days back; a follow-up's own words win; the count takes both ends."""
    label, first, last = ga._egg_span("and last week")
    assert label == "last week" and (date.today() - first).days == 13 and (date.today() - last).days == 7
    assert ga._egg_span("how many eggs this week") is None
    entries = [SimpleNamespace(flock_id="f", kind="eggs", date=(date.today() - timedelta(days=d)).isoformat(), count=4)
               for d in (7, 10, 13, 14, 2)]
    assert ga.eggs_between(entries, "f", first, last) == 12


def test_last_week_is_said_beside_this_week():
    """A flock with 3 eggs a day: 21 last week, against this week's."""
    flock = SimpleNamespace(flock_id="f", name="The girls")
    entries = [SimpleNamespace(flock_id="f", kind="eggs", date=(date.today() - timedelta(days=d)).isoformat(), count=3)
               for d in range(14)]
    context = SimpleNamespace(flock=SimpleNamespace(flocks=[flock], entries_for=lambda fid: entries))
    assert ga._eggs_in_span(context, ga._egg_span("last week")) == "The girls: 21 eggs last week, against 21 this week."
