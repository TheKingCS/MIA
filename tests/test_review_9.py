"""
tests.test_review_9
=====================

The ninth review's other findings (2026-11-25), each kept fixed: a date is read in more of the ways it's said (last
Friday, Nov 20th, Sept 3, 11-20-2026, 2026/11/20, Feb 29, a day-first 25/11/2026), and an update with one it can't
read keeps the entry's own date; a span said ("for a week") wins over hours; "4 people including 2 kids" is a
breakdown; and a real "a tragedy" in an answer's first line stays.
"""

from datetime import date

from core import homestead_sums as sums
from core.budget_manager import read_date
from core.personality import without_copied_example


def test_dates_said_in_more_ways_are_read():
    today = date.today()
    assert read_date("11-20-2026") == "2026-11-20" and read_date("2026/11/20") == "2026-11-20"
    assert read_date("25/11/2026") == "2026-11-25" and read_date("05/11/2026") == "2026-05-11"
    assert read_date("Nov 20, 2025") == "2025-11-20" and read_date("Feb 29").endswith("-02-29")
    weekday = date.fromisoformat(read_date("last friday"))
    assert weekday.weekday() == 4 and 0 < (today - weekday).days <= 7
    assert read_date("null") is None and read_date("March") is None


def test_an_update_with_a_date_it_cant_read_keeps_the_entrys(tmp_path):
    from types import SimpleNamespace

    from core.budget_manager import BudgetManager

    budget = BudgetManager(SimpleNamespace(events=None, config=None), data_dir=tmp_path)
    entry = budget.add_expense(amount=10, category="Other", date="2026-11-03")
    assert budget.update_expense(entry.entry_id, date="sometime soon").date == "2026-11-03"
    assert budget.update_expense(entry.entry_id, date="Nov 5, 2026").date == "2026-11-05"


def test_a_span_said_wins_over_hours_and_including_is_a_breakdown():
    assert sums.days_in("water for a week, a pump runs 24 hours") == 7
    assert sums.days_in("enough for a month, 5 gallons every 24 hours") == 30
    assert sums.days_in("water for 72 hours at a gallon a day each") == 3
    assert sums.people_in("4 people including 2 kids") == 4 and sums.people_in("for 4 people (2 kids)") == 4
    assert sums.people_in("for 2 people and 2 kids") == 4


def test_a_real_tragedy_stays():
    text = "Romeo and Juliet is a tragedy. It was written by Shakespeare."
    assert without_copied_example(text, "tell me about romeo and juliet") == text
