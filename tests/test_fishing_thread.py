"""
tests.test_fishing_thread
===========================

The fishing conversation check's fixes (2026-11-26): a catch said whole read in code (one 3 pound bass, never three
bass), "when's the best time to go back?" after her catch reply, and spending on fishing gear from the expenses that
name it.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, catch_actions, her_asks


def test_a_catch_as_said():
    assert catch_actions.parse("I caught a 3 pound bass at the pond this morning") == {
        "species": "bass", "count": 1, "weight": 3.0, "where": "pond"}
    assert catch_actions.parse("caught an 18 inch largemouth bass on a green pumpkin worm") == {
        "species": "largemouth bass", "count": 1, "length": 18.0, "bait": "green pumpkin worm"}
    assert catch_actions.parse("I caught three crappie at the lake") == {"species": "crappie", "count": 3,
                                                                          "where": "lake"}
    for said in ("I caught a cold", "did I catch a bass?", "I caught a 3 pound bass yesterday", "two 3 pound bass"):
        assert catch_actions.parse(said) is None, said


def test_going_back_after_a_catch():
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append(n) or "times"))
    assert her_asks.reply(context, "Logged a bass at pond. 3 fish logged in all.", "when's the best time to go back?") \
        == "times"
    assert ran == ["best_time_to_fish"]
    assert her_asks.reply(context, "Done.", "when's the best time to go back?") is None


def test_spending_on_a_thing_by_its_description():
    rows = [SimpleNamespace(entity_id="", date="2026-05-02", description="Fishing reel", amount=60.0),
            SimpleNamespace(entity_id="", date="2026-08-02", description="fishing line", amount=12.5),
            SimpleNamespace(entity_id="", date="2025-08-02", description="fishing rod", amount=90.0),
            SimpleNamespace(entity_id="", date="2026-08-03", description="Groceries", amount=40.0)]
    book = SimpleNamespace(all_expenses=lambda: rows)
    said = assistant_turn._spent_by_words(book, "fishing gear", "this year", date(2026, 11, 26))
    assert said == "$72.50 this year on fishing gear, from 2 expenses that name it."
    none = assistant_turn._spent_by_words(book, "golf gear", "this year", date(2026, 11, 26))
    assert none.startswith("Nothing logged this year with \"golf\"")
