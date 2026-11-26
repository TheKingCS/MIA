"""
tests.test_firewood_ask
=========================

"About 4" answering her own "How many cords does a winter take you?" is kept as his winter's figure
(core/firewood.answer_to_ask, brainstorm round 19), and "do I have enough firewood?" is her check's own words.
"""

from types import SimpleNamespace

from core import assistant_turn, firewood


def test_a_bare_number_after_her_ask_is_kept(monkeypatch):
    kept = []
    from core import assistant_today_actions

    monkeypatch.setattr(assistant_today_actions, "_action_set_preparedness",
                        lambda c, a: kept.append(a) or "Kept.")
    monkeypatch.setattr(firewood, "say", lambda c: "Checked.")
    asked = "Firewood: none. " + firewood.ASK + " A wood stove..."
    assert firewood.answer_to_ask(SimpleNamespace(), asked, "about 4 cords") == "Kept. Checked."
    assert firewood.answer_to_ask(SimpleNamespace(), asked, "maybe 6 face cords") == "Kept. Checked."
    assert kept == [{"firewood_cords": 4.0}, {"firewood_cords": 2.0}]
    assert firewood.answer_to_ask(SimpleNamespace(), "How are you?", "about 4") is None
    assert firewood.answer_to_ask(SimpleNamespace(), asked, "about 4 trucks") is None
    assert firewood.answer_to_ask(SimpleNamespace(), asked, "400") is None


def test_the_words_reach_the_check():
    pattern = next(p for n, p, _w in assistant_turn._OWN_TOOLS if n == "firewood_check")
    for words in ("do I have enough firewood for the winter?", "how much firewood do I have left?",
                  "will my woodpile last the winter?"):
        assert pattern.match(words), words
    assert not pattern.match("do I have enough firewood if it's a cold winter?")
