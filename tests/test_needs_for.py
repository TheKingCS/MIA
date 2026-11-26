"""
tests.test_needs_for
======================

"What do I need for the chili?" (core/assistant_domain_actions.needs_for, the live sweep 2026-11-26): a saved
recipe's missing ingredients and the offer to list them; a name that isn't his recipe is the model's.
"""

from types import SimpleNamespace

from core import assistant_domain_actions as dom
from core import assistant_turn


def _context():
    chili = SimpleNamespace(recipe_id="r1", name="Venison Chili", ingredients=[{"name": "ground venison"}], locked=False)
    kitchen = SimpleNamespace(all_recipes=lambda: [chili], recipes_makeable_now=lambda: [(chili, ["ground venison"])])
    return SimpleNamespace(kitchen=kitchen)


def test_a_recipes_missing_ingredients(monkeypatch):
    monkeypatch.setattr(dom, "_find_recipe", lambda c, name: (c.kitchen.all_recipes()[0], None) if "chili" in name
                        else (None, "no"))
    said = dom.needs_for(_context(), "chili")
    assert said == ('For Venison Chili you still need: ground venison; the rest is in your pantry. Say "add what I '
                    'need for the venison chili to my grocery list" and I\'ll put it on.')
    assert dom.needs_for(_context(), "a chicken coop") is None
    assert dom.needs_for(_context(), "the chili bowls") is None, "every word of the dish in the recipe's name"


def test_the_words_reach_it(monkeypatch):
    monkeypatch.setattr(dom, "needs_for", lambda c, d: f"for {d}")
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "What do I need for the chili?") == "for chili"
