"""
tests.test_her_asks_build
===========================

A build she offered to work out, kept up across turns (core/her_asks, the conversation check 2026-11-26): its size is
its materials, "how much would it cost?" asks the size, and "add it to my projects" adds it.
"""

from types import SimpleNamespace

from core import her_asks

OFFER = ("Good project. I can work out the materials and cuts for a shed at your size, what they'd cost from your "
         "prices, and what's already on hand. Say \"materials for a shed\" and I'll do it, or give me your size.")


def test_the_size_cost_and_add(monkeypatch):
    from core import assistant_plan_actions

    monkeypatch.setattr(assistant_plan_actions, "materials_reply", lambda c, w: f"list[{w}]")
    for said in ("a 10 by 12", "what about a 10 by 12?", "10x12", "make it 10' by 12'"):
        assert her_asks.reply(SimpleNamespace(), OFFER, said) == "list[materials for a 10 by 12 shed]", said
    ask = her_asks.reply(SimpleNamespace(), OFFER, "how much would the lumber cost?")
    assert ask.startswith("For the shed, what size?")
    assert her_asks.reply(SimpleNamespace(), ask, "what about a 10 by 12?") == "list[materials for a 10 by 12 shed]"
    ran = []
    context = SimpleNamespace(assistant_actions=SimpleNamespace(execute=lambda c, n, a: ran.append((n, a)) or "Added."))
    assert her_asks.reply(context, OFFER, "add it to my projects") == "Added."
    assert ran == [("add_project", {"name": "Shed"})]
    assert her_asks.reply(context, OFFER, "what's the weather?") is None
    ran.clear()
    listed = "10 x 12 ft gable shed:\n- 11 2x8 x 10 ft (joists)"
    assert her_asks.reply(context, listed, "add it to my projects", (OFFER, "For the shed, what size?", listed)) == "Added."
    assert ran == [("add_project", {"name": "Shed"})]
    assert her_asks.reply(context, listed, "a 10 by 12", (OFFER, listed)) is None


def test_her_offers_own_words_reach_the_calculators():
    from core.assistant_plan_actions import _MATERIALS_ASK

    for words in ("materials for a 10 by 12 shed", "materials for 100 feet of privacy fence"):
        assert _MATERIALS_ASK.search(words), words
