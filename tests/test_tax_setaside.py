"""
tests.test_tax_setaside
=========================

"How much should I set aside for taxes?" (core/tax_setaside.py): self-employment tax is 15.3% of 92.35% of the
profit from $400 of earnings, income tax at 12% and 22% side by side with a bracket he gives, the next 1040-ES date, a loss
owes nothing, and outside the US it says it's US-only.
"""

from datetime import date
from types import SimpleNamespace

from core import tax_setaside as tx


class _Ledger:
    """A ledger with one profit figure, checking the dates it's asked for."""

    def __init__(self, profit):
        """The profit it reports."""
        self.profit, self.asked = profit, None

    def net_profit(self, start=None, end=None):
        """The profit, remembering the window."""
        self.asked = (start, end)
        return self.profit


def _context(monkeypatch, profit, country="US"):
    """A context with that ledger, in that country."""
    from core import region

    monkeypatch.setattr(region, "country_of", lambda context: country)
    return SimpleNamespace(ledger=_Ledger(profit))


def test_self_employment_tax_and_the_next_due_date():
    """$10,000 profit: $1,412.95; $400 of earnings is the floor; the dates roll through the year."""
    assert tx.se_tax(10_000) == 1412.95
    assert tx.se_tax(400) == 0.0 and tx.se_tax(500) > 0
    assert tx.next_due(date(2026, 3, 1)) == date(2026, 4, 15)
    assert tx.next_due(date(2026, 6, 16)) == date(2026, 9, 15)
    assert tx.next_due(date(2026, 11, 24)) == date(2027, 1, 15)
    assert tx.next_due(date(2026, 1, 10)) == date(2026, 1, 15)
    assert tx.rate_in("I'm in the 22% bracket") == 22 and tx.rate_in("0.12") == 12 and tx.rate_in("none") is None


def test_the_answer_with_and_without_his_bracket(monkeypatch):
    """12% and 22% side by side, a given 24% among them, never called his; this year's window; the due date and the
    preparer."""
    context = _context(monkeypatch, 10_000)
    said = tx.say(context, date(2026, 11, 24))
    assert context.ledger.asked == ("2026-01-01", "2026-11-24")
    assert "$10,000.00" in said and "$1,412.95" in said and "at 12% it's about $1,200.00, so $2,612.95 in all" in said
    assert "at 22% it's about $2,200.00" in said and "January 15, 2027" in said and "tax preparer" in said
    given = tx.say(context, date(2026, 11, 24), "24%")
    assert "at 12%" in given and "at 22%" in given and "at 24% it's about $2,400.00" in given
    assert "your 24" not in given


def test_a_loss_owes_nothing_and_another_country_is_told_its_us_only(monkeypatch):
    """No profit: nothing yet; set to Canada: US-only."""
    assert "no self-employment tax" in tx.say(_context(monkeypatch, -50), date(2026, 5, 1))
    assert "US self-employment tax only" in tx.say(_context(monkeypatch, 5000, "CA"), date(2026, 5, 1))
