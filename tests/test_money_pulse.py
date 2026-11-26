"""
tests.test_money_pulse
========================

The money pulse (core/money_pulse.py, 2026-11-25): the category drifting furthest over its usual pace, what's due in
the next seven days and the tightest week ahead, from his own budget; said on Sundays once a week through the gate,
and on "how's my money this week?".
"""

from datetime import date, datetime, timedelta
from types import SimpleNamespace

from core import assistant_turn, money_pulse


class _Budget:
    """A budget with three months of usual groceries and this month running hot, one bill due and one income."""

    def __init__(self, today):
        self.today = today

    def total_expenses_by_category(self, start, end, entity_id=""):
        if end == self.today.isoformat():
            return {"Groceries": 400.0, "Utilities": 100.0}
        return {"Groceries": 400.0, "Utilities": 200.0}

    def all_bills(self):
        due = self.today + timedelta(days=3)
        return [SimpleNamespace(name="Electric", amount=150.0, due_date=due.isoformat(), recurrence="monthly",
                                last_paid_date=None, category="Utilities", entity_id="", bill_id="b1")]

    def all_income_sources(self):
        return []

    def all_debts(self):
        return []

    def all_expenses(self):
        """This month's groceries, a business's lumber and last month's run, to pick the biggest from."""
        return [SimpleNamespace(category="Groceries", amount=a, description=d, payee="", date=day, entity_id=e)
                for a, d, day, e in ((180.0, "Costco run", "2026-11-03", ""), (40.0, "Milk", "2026-11-10", ""),
                                     (300.0, "Shop lumber", "2026-11-05", "llc"), (90.0, "Feed store", "2026-11-12", ""),
                                     (500.0, "Last month", "2026-10-30", ""))]


def test_the_pulse_names_the_drift_and_whats_due(monkeypatch):
    from core import budget_manager

    today = date(2026, 11, 15)
    monkeypatch.setattr(budget_manager, "next_bill_due_date", lambda b: today + timedelta(days=3))
    said = money_pulse.line(SimpleNamespace(budget=_Budget(today)), today)
    assert said.startswith("Groceries is running"), said
    assert "The biggest: Costco run ($180.00) and Feed store ($90.00)." in said, said
    assert "Utilities" not in said
    assert "Due this week:" in said and "Electric" in said
    assert "Tightest week ahead" not in said, "no income logged: no week is called tight"


def test_rent_paid_in_one_go_is_never_paced_as_drift():
    class Rent(_Budget):
        def total_expenses_by_category(self, start, end, entity_id=""):
            return {"Mortgage/Rent": 1500.0}

    assert money_pulse.drift(SimpleNamespace(budget=Rent(date(2026, 11, 8))), date(2026, 11, 8)) is None


def test_nothing_to_say_says_how_to_start():
    class Empty(_Budget):
        def total_expenses_by_category(self, start, end, entity_id=""):
            return {}

        def all_bills(self):
            return []

    said = money_pulse.say(SimpleNamespace(budget=Empty(date(2026, 11, 15))), date(2026, 11, 15))
    assert said.startswith("Nothing to take a pulse from yet")


def test_it_is_offered_only_on_sundays_once_a_week(monkeypatch):
    monkeypatch.setattr(money_pulse, "line", lambda c, t=None: "the pulse")
    assert money_pulse.offer(None, datetime(2026, 11, 24, 9)) == []
    said = money_pulse.offer(None, datetime(2026, 11, 29, 9))
    assert len(said) == 1 and said[0].topic == "money_pulse" and said[0].fingerprint == "money-pulse-2026-W48"


def test_the_words_reach_the_pulse(monkeypatch):
    monkeypatch.setattr(money_pulse, "say", lambda c, t=None: "the pulse")
    for words in ("How's my money this week?", "money pulse", "how's money looking", "give me the money pulse.",
                  "how's my money looking this week", "how are my finances this week"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "the pulse", words
    for words in ("how's my money", "how is money tight this week"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) != "the pulse", words
