"""
tests.test_money_ahead
========================

The next 13 weeks of money (core/money_ahead.py, brainstorm 6.1): bills, income and debt minimums by week from his
budget, the tight weeks worst first, every overdue and late one said now, a debt never counted twice (paid this
month, or already a bill), never a bank balance it can't know.
"""

from datetime import date
from types import SimpleNamespace

from core import money_ahead as ma
from core.budget_manager import Bill, Debt, IncomeSource

TODAY = date(2026, 11, 23)  # a Monday


def _bill(name, amount, due, recurrence="monthly", paid=None):
    return Bill(bill_id=name, name=name, amount=amount, due_date=due, recurrence=recurrence, last_paid_date=paid)


def _pay(name, amount, nxt, recurrence="biweekly", got=None):
    return IncomeSource(source_id=name, name=name, expected_amount=amount, next_date=nxt, recurrence=recurrence,
                        last_received_date=got)


def test_monthly_bills_fall_on_their_day_each_month():
    moves = ma.flows([_bill("Rent", 1000, "2026-12-01")], [], [], TODAY)
    assert [m["day"] for m in moves] == [date(2026, 12, 1), date(2027, 1, 1), date(2027, 2, 1)]


def test_an_overdue_bill_and_late_pay_count_now_and_say_so():
    moves = ma.flows([_bill("Power", 120, "2026-11-15")], [_pay("Paycheck", 900, "2026-11-20", None)], [], TODAY)
    now = [m for m in moves if m["day"] == TODAY]
    assert {(m["what"], m["note"]) for m in now} == {("Power", "overdue"), ("Paycheck", "late")}


def test_debt_minimums_come_monthly_on_the_day_last_paid_or_the_first():
    debts = [Debt(debt_id="c", name="Card", balance=2000, interest_rate=24, minimum_payment=60,
                  last_payment_date="2026-11-10"),
             Debt(debt_id="l", name="Loan", balance=500, interest_rate=5, minimum_payment=50),
             Debt(debt_id="p", name="Paid off", balance=0, interest_rate=5, minimum_payment=50)]
    moves = ma.flows([], [], debts, TODAY)
    card = [m["day"] for m in moves if m["what"] == "Card minimum"]
    loan = [m for m in moves if m["what"] == "Loan minimum"]
    assert card == [date(2026, 12, 10), date(2027, 1, 10), date(2027, 2, 10)]
    assert loan[0]["day"] == date(2026, 12, 1) and "1st" in loan[0]["note"]
    assert not any(m["what"] == "Paid off minimum" for m in moves)


def test_weeks_add_up_and_the_tightest_comes_first():
    moves = ma.flows([_bill("Rent", 1000, "2026-12-01"), _bill("Phone", 80, "2026-12-03")],
                     [_pay("Paycheck", 900, "2026-11-27")], [], TODAY)
    by_week = ma.weeks(moves, TODAY)
    assert len(by_week) == 13 and by_week[0]["start"] == TODAY
    assert by_week[0]["in"] == 900 and by_week[1]["out"] == 1080 and by_week[1]["in"] == 0
    assert ma.tight(by_week)[0]["start"] == date(2026, 11, 30)


def test_say_gives_totals_tight_weeks_and_no_balance(monkeypatch):
    budget = SimpleNamespace(all_bills=lambda: [_bill("Rent", 1000, "2026-12-01")],
                             all_income_sources=lambda: [_pay("Paycheck", 900, "2026-11-27")],
                             all_debts=lambda: [])
    said = ma.say(SimpleNamespace(budget=budget), TODAY)
    assert "The next 13 weeks" in said and "Tightest: the week of November 30" in said and "Rent" in said
    assert "no bank balance" in said


def test_an_empty_budget_says_what_to_add():
    assert "Add them in Budget" in ma.say(SimpleNamespace(budget=None), TODAY)
    assert ma.page(SimpleNamespace(budget=None), TODAY)["any"] is False


def test_every_missed_occurrence_counts_now_not_only_the_first():
    moves = ma.flows([_bill("Water", 40, "2026-09-15", paid="2026-09-15")], [], [], TODAY)
    late = [m for m in moves if m["note"] == "overdue"]
    assert len(late) == 2 and all(m["day"] == TODAY for m in late)  # October's and November's


def test_a_debt_paid_this_month_or_kept_as_a_bill_isnt_counted_twice():
    paid = Debt(debt_id="c", name="Card", balance=900, interest_rate=20, minimum_payment=40,
                last_payment_date="2026-11-23")
    assert [m["day"] for m in ma.flows([], [], [paid], TODAY)][0] == date(2026, 12, 23)
    both = ma.flows([_bill("Card payment", 40, "2026-12-05")], [], [paid], TODAY)
    assert not any(m["what"] == "Card minimum" for m in both)
