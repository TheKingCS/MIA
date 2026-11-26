"""
tests.test_side_hustle
========================

"What's a good side hustle for me?" (core/side_hustle.py, the live sweep 2026-11-26): ideas from what he already
sells, keeps, learns and owns, each with its next step; nothing guessed.
"""

from datetime import date
from types import SimpleNamespace

from core import assistant_turn, side_hustle

TODAY = date(2026, 11, 26)


def test_ideas_come_from_his_records():
    context = SimpleNamespace(
        ledger=SimpleNamespace(all_revenue=lambda: [SimpleNamespace(product_id="p1", amount=240.0, date="2026-10-01")]),
        products=SimpleNamespace(all_products=lambda: [SimpleNamespace(product_id="p1", name="Cutting Board")]),
        flock=SimpleNamespace(flocks=[SimpleNamespace(hens=6)]),
        paths=SimpleNamespace(started=lambda: ["woodworking"]),
        maintenance=SimpleNamespace(all_assets=lambda: [SimpleNamespace(name="Log Splitter")]))
    said = side_hustle.say(context, TODAY)
    assert said.startswith("From what you already have: 1. More of your Cutting Board: it's brought in $240.00")
    assert "Eggs from your hens" in said and "custom pieces and repairs" in said.lower()
    assert "Splitting and selling firewood, with your Log Splitter." in said


def test_a_camper_is_never_hauling_and_mowing_says_check_first():
    context = SimpleNamespace(maintenance=SimpleNamespace(all_assets=lambda: [SimpleNamespace(name="Travel Trailer"),
                                                                              SimpleNamespace(name="Lawnmower")]))
    said = side_hustle.say(context, TODAY)
    assert "hauling" not in said and "Mowing in your area, with your Lawnmower. Check your insurance" in said


def test_nothing_in_his_records_says_so():
    assert side_hustle.say(SimpleNamespace(), TODAY).startswith("I don't have enough in your records")


def test_the_words_reach_it(monkeypatch):
    monkeypatch.setattr(side_hustle, "say", lambda c, t=None: "ideas")
    for words in ("What's a good side hustle for me?", "how can I make some extra money"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "ideas", words
