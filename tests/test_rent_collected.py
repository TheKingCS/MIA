"""
tests.test_rent_collected
===========================

"How much rent did I collect this month?" (core/rent_collected.py): this month, last month, this year or a named month
read from his words, rent summed by property from his records with the total, and a property that paid before but
not yet this month named; no properties says how to add one.
"May" as a verb isn't May, and last year is the whole of it.
"""

from datetime import date
from types import SimpleNamespace

from core import rent_collected as rc


def test_the_span_his_words_name():
    """From 2026-11-24: last month is October, "august" the last August, nothing named this month; a follow-up's own
    words first."""
    today = date(2026, 11, 24)
    assert rc.span_of("and last month?", today)[1:] == (date(2026, 10, 1), date(2026, 10, 31))
    assert rc.span_of("rent in august", today)[1:] == (date(2026, 8, 1), date(2026, 8, 31))
    assert rc.span_of("And last month? (after: rent this month?)", today)[0] == "in October"
    assert rc.span_of("how much rent?", today)[0] == "so far this month"


def test_rent_by_property_and_the_one_not_paid_yet(monkeypatch):
    """Main St paid $1,800 in November, Oak Ave paid in October but not yet: both said."""
    from core import region

    monkeypatch.setattr(region, "money", lambda amount, spec=",.2f": f"${amount:,.2f}")
    rows = {"a": [("2026-11-02", 1800.0), ("2026-10-02", 1800.0)], "b": [("2026-10-05", 950.0)]}

    def income(pid, start, end):
        return [SimpleNamespace(amount=a, date=d) for d, a in rows[pid] if start <= d <= end]

    estate = SimpleNamespace(all_properties=lambda: [SimpleNamespace(property_id="a", name="Main St"),
                                                     SimpleNamespace(property_id="b", name="Oak Ave")],
                             income_for_property=income)
    said = rc.say(SimpleNamespace(real_estate=estate), "how much rent this month?", date(2026, 11, 24))
    assert said == ("Rent collected so far this month: $1,800.00, from Main St $1,800.00. Nothing logged yet this "
                    "month from Oak Ave, which paid in the months before.")
    last = rc.say(SimpleNamespace(real_estate=estate), "last month", date(2026, 11, 24))
    assert last.startswith("Rent collected in October: $2,750.00 (Main St $1,800.00; Oak Ave $950.00)")
    assert rc.say(SimpleNamespace(real_estate=None)).startswith("No properties in MIA yet")



def test_may_as_a_verb_and_last_year():
    """"Some tenants may be late" isn't May; "in may" is; last year is the whole of it."""
    today = date(2026, 11, 24)
    assert rc.span_of("how much rent did I collect? Some tenants may be late", today)[0] == "so far this month"
    assert rc.span_of("rent in may", today)[0] == "in May 2026"
    assert rc.span_of("rent last year", today)[1:] == (date(2025, 1, 1), date(2025, 12, 31))
