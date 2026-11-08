"""
tests.test_voice_corrections
==============================

Fixing and planning by voice (DEC-0125, core/assistant_correction_actions.py):
each tool finds the record from the words said and runs the screen's own
action kind (undoable); unclear names are asked about and change nothing.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_correction_actions as fix

TODAY = date(2026, 11, 8)  # a Sunday


class _Actions:
    """Keeps each proposal and runs it."""

    def __init__(self):
        """Nothing yet."""
        self.proposed = []

    def propose(self, context, kind, params, proposed_by):
        """Keeps it."""
        self.proposed.append((kind, params))
        return SimpleNamespace(proposal_id="p")

    def approve(self, context, proposal_id):
        """Done."""
        return SimpleNamespace(status="executed", result="Done.")


def _context():
    """A kitchen and a budget with a few records."""
    kitchen = SimpleNamespace(
        all_grocery_items=lambda: [SimpleNamespace(item_id="g1", name="Milk"), SimpleNamespace(item_id="g2", name="Oat milk")],
        all_pantry_items=lambda: [SimpleNamespace(item_id="p1", name="Flour")],
        all_recipes=lambda: [SimpleNamespace(recipe_id="r1", name="Turkey Chili"), SimpleNamespace(recipe_id="r2", name="Cornbread")])
    budget = SimpleNamespace(
        all_bills=lambda: [SimpleNamespace(bill_id="b1", name="Electric"), SimpleNamespace(bill_id="b2", name="Water")],
        all_expenses=lambda: [SimpleNamespace(entry_id="e1", description="Pizza", payee="", date="2026-11-01"),
                              SimpleNamespace(entry_id="e2", description="Pizza night", payee="", date="2026-11-07")])
    return SimpleNamespace(kitchen=kitchen, budget=budget, actions=_Actions())


def test_an_exact_name_wins_and_an_unclear_one_is_asked_about():
    """"Milk" is Milk, not Oat milk; "milk" alone in two names is fine because one is exact; "bread" in none asks."""
    c = _context()
    assert "undo that" in fix._action_remove_grocery_item(c, {"item": "milk"})
    assert c.actions.proposed == [("grocery.delete", {"item_id": "g1"})]
    c = _context()
    assert fix._action_remove_grocery_item(c, {"item": "bread"}) == "I don't see a grocery item called bread."
    assert fix._action_remove_grocery_item(c, {"item": "m"}).startswith("Which grocery item?") and not c.actions.proposed


def test_each_correction_runs_its_screen_s_own_action():
    """The kinds and params each tool proposes."""
    cases = [
        (fix._action_clear_checked_groceries, {}, ("grocery.clear_checked", {})),
        (fix._action_remove_pantry_item, {"item": "flour"}, ("pantry.delete", {"item_id": "p1"})),
        (fix._action_rate_recipe, {"recipe": "chili", "stars": "5 stars"}, ("recipe.rate", {"recipe_id": "r1", "rating": 5})),
        (fix._action_favorite_recipe, {"recipe": "cornbread"}, ("recipe.favorite", {"recipe_id": "r2", "favorite": True})),
        (fix._action_favorite_recipe, {"recipe": "cornbread", "favorite": "no"},
         ("recipe.favorite", {"recipe_id": "r2", "favorite": False})),
        (fix._action_change_bill, {"bill": "electric", "amount": "130"}, ("bill.edit", {"bill_id": "b1", "amount": "130"})),
        (fix._action_delete_bill, {"bill": "water"}, ("bill.delete", {"bill_id": "b2"})),
        (fix._action_delete_expense, {"expense": "pizza"}, ("expense.delete", {"entry_id": "e2"})),  # the newest
    ]
    for handler, args, expected in cases:
        c = _context()
        handler(c, args)
        assert c.actions.proposed == [expected], handler.__name__


def test_a_meal_is_planned_on_the_day_said(monkeypatch):
    """"Plan the chili for dinner Tuesday": the next Tuesday, dinner, one serving."""
    class _Date(date):
        """date, with today fixed."""

        @classmethod
        def today(cls):
            """The test's Sunday."""
            return TODAY

    monkeypatch.setattr(fix, "date", _Date)
    c = _context()
    fix._action_plan_meal(c, {"recipe": "turkey chili", "day": "Tuesday", "meal": "dinner"})
    assert c.actions.proposed == [("meal.plan", {"date": "2026-11-10", "meal": "dinner", "recipe_id": "r1", "servings": 1})]


def test_days_are_read_from_words_or_dates():
    """Today, tomorrow, the next weekday (today counts), a date; anything else isn't a day."""
    assert fix.day_of("today", TODAY) == "2026-11-08" and fix.day_of("tomorrow", TODAY) == "2026-11-09"
    assert fix.day_of("Tuesday", TODAY) == "2026-11-10" and fix.day_of("on sunday", TODAY) == "2026-11-08"
    assert fix.day_of("2026-12-01", TODAY) == "2026-12-01" and fix.day_of("someday", TODAY) is None


def test_a_bill_change_with_nothing_changed_asks_what_changed():
    """No amount and no date: a question, nothing proposed."""
    c = _context()
    assert fix._action_change_bill(c, {"bill": "electric"}).startswith("What changed about Electric")
    assert not c.actions.proposed


def test_the_real_screen_actions_take_what_the_tools_send(tmp_path, monkeypatch):
    """On real stores: the bill's amount changes, the grocery item goes, and "undo that" brings the item back."""
    from core.actions import ActionCenter
    from core.undo_log import undo_last
    from core.person_settings import person_id
    from tests.engine_world import build_world

    w = build_world(tmp_path, monkeypatch)
    w.actions = ActionCenter()
    bill = w.budget.add_bill("Electric", 120.0, "2026-11-03")
    w.kitchen.add_grocery_item("Milk")
    assert "undo that" in fix._action_change_bill(w, {"bill": "electric", "amount": "130"})
    assert w.budget.get_bill(bill.bill_id).amount == 130.0
    assert "undo that" in fix._action_remove_grocery_item(w, {"item": "milk"})
    assert [i.name for i in w.kitchen.all_grocery_items()] == []
    undo_last(w, person_id(w))
    assert [i.name for i in w.kitchen.all_grocery_items()] == ["Milk"]
