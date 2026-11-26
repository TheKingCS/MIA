"""
tests.test_cross_routes2
==========================

The cross-route review's "falls to the model" sentences, answered in code: spending on a thing in any period, when
he last paid rent or the truck, reports asked indirectly, and "remind me every month to ...".
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, reminders_view, standing_reports


def test_spending_on_a_thing_last_week():
    calls = []
    budget = SimpleNamespace(total_expenses_by_category=lambda s, e: calls.append((s, e)) or {"Transportation": 60.0})
    said = assistant_turn._spent_on_reply(SimpleNamespace(budget=budget), "how much did I spend on gas last week")
    assert said == "$60.00 on Transportation last week, from what you've logged."


def test_when_he_last_paid_rent_or_the_truck():
    rent = SimpleNamespace(name="Rent", last_paid_date="2026-11-01")
    truck = SimpleNamespace(name="Truck Loan", debt_type="Auto Loan", last_payment_date="2026-11-10")
    budget = SimpleNamespace(all_bills=lambda: [rent], all_debts=lambda: [truck])
    context = SimpleNamespace(budget=budget)
    assert reminders_view.last_in_history(context, "pay rent", date(2026, 11, 26)) == \
        "You last paid Rent on Sunday, November 1."
    assert reminders_view.last_in_history(context, "pay the truck", date(2026, 11, 26)) == \
        "You last paid on Truck Loan on Tuesday, November 10."


def test_paying_a_bill_in_general_reads_the_history(monkeypatch):
    from core import life_events

    monkeypatch.setattr(life_events, "events_for", lambda c, types=None, **k: [])
    said = reminders_view.last_in_history(SimpleNamespace(budget=SimpleNamespace(all_bills=lambda: [],
                                                                                 all_debts=lambda: [])),
                                          "pay a bill", date(2026, 11, 26))
    assert said.startswith("I don't have a time you paid a bill logged yet")


def test_reports_said_indirectly_are_asked_directly():
    assert standing_reports.parse("every Sunday tell me what my week looks like")["question"] == \
        "What does my week look like?"
    assert standing_reports.parse("every night tell me what I did today")["question"] == "What did I do today?"
    assert standing_reports.parse("every week tell me what reminders I have")["question"] == \
        "What reminders do I have?"


def test_remind_me_every_month_to():
    found = assistant_turn._REMIND_MONTHLY.match("remind me every month to rotate the feed")
    assert found and found.group("what3") == "rotate the feed"
