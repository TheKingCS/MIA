"""The payoff arithmetic behind "when will my debts be paid off?" and
"what if I put an extra $200 toward it?" (core/debt_math.py)."""

from datetime import date
from types import SimpleNamespace

from core.debt_math import simulate

TODAY = date(2026, 10, 30)


def debt(name, balance, rate, minimum, **kw):
    return SimpleNamespace(name=name, balance=balance, interest_rate=rate, minimum_payment=minimum, **kw)


def test_no_interest_is_simple_division():
    p = simulate([debt("Loan", 1000, 0, 100)], today=TODAY)
    assert p.months == 10 and p.debt_free == "2027-07" and p.interest == 0


def test_interest_and_the_extra_shorten_it():
    base = simulate([debt("Card", 5000, 24, 150)], today=TODAY)
    more = simulate([debt("Card", 5000, 24, 150)], extra=200, today=TODAY)
    assert base.months > more.months and base.interest > more.interest > 0
    assert more.monthly == 350


def test_the_rollover_goes_to_the_next_debt():
    two = [debt("Small", 500, 0, 100), debt("Big", 2000, 0, 100)]
    p = simulate(two, today=TODAY)
    small, big = p.debts
    assert small.months == 5
    # Big gets 100 for 5 months (500), then 200 a month for the remaining 1500: 7.5 -> 8 more months.
    assert big.months == 13 and p.months == 13


def test_a_minimum_below_the_interest_is_never_paid_off():
    p = simulate([debt("Card", 10000, 30, 100)], today=TODAY)  # 250 a month of interest
    assert p.months is None and p.debts[0].paid_off is None


def test_a_promo_rate_until_it_ends():
    promo = simulate([debt("Card", 1200, 25, 100, promo_apr=0.0, promo_expires_date="2028-01-01")], today=TODAY)
    assert promo.months == 12 and promo.interest == 0
