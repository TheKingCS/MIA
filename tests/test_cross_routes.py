"""
tests.test_cross_routes
=========================

The cross-route review of 2026-11-26: sentences two routes reached for, sent where they belong. A reminder's task
never ends on a dangling word, a store's sale or the truck's gas is never a homestead watch, a bill paid is never a
stray expense, a dozen cutting boards is never the eggs' price, a command is never answered as a question.
"""

from types import SimpleNamespace

from core import assistant_turn, condition_watch


def test_a_reminder_with_a_deadline_is_never_an_event_named_before():
    ran = []
    actions = SimpleNamespace(execute=lambda c, n, a: ran.append(a) or "added")
    assert assistant_turn._reminder_reply(SimpleNamespace(assistant_actions=actions),
                                          "remind me to order feed before Friday") is None
    assert ran == []


def test_a_watch_never_on_a_store_the_truck_or_a_weekday():
    for words in ("tell me when the feed store has a sale on feed", "tell me when the truck is low on gas",
                  "warn me if it's going to rain on Saturday"):
        assert condition_watch.parse(words) is None, words
    assert condition_watch.parse("tell me if it freezes tonight")["kind"] == "freeze"


def test_a_dozen_cutting_boards_is_never_the_eggs_price():
    assert not assistant_turn._EGG_PRICE.search("what should I charge for a dozen cutting boards")
    assert assistant_turn._EGG_PRICE.search("how much should I charge per dozen")
    assert assistant_turn._EGG_PRICE.search("what should I charge for a dozen eggs")


def test_a_command_is_never_answered_as_a_question():
    ask = lambda w: assistant_turn._own_tool_reply(SimpleNamespace(), w)  # noqa: E731
    for words in ("remind me to check the truck's emergency kit", "I put jumper cables in the truck kit",
                  "remind me to ask the vet why the hens aren't laying"):
        said = ask(words)
        assert not (said or "").startswith(("Ready.gov", "Your hens")), words
    assert ask("what do I need?") is None or "trip" not in (ask("what do I need?") or "")
    assert assistant_turn._mains_reply(None, "check if the truck's power outlet is live") is None


def test_out_of_oil_or_water_is_never_the_grocery_list():
    for words in ("I'm out of oil", "we're out of water"):
        assert not assistant_turn._groceries(SimpleNamespace(), words.split("of ", 1)[1]), words
