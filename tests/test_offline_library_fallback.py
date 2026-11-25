"""
tests.test_offline_library_fallback
=====================================

With no packs or nothing matching (the live sweep, 2026-11-25), the offline library's look-up tells the model to
answer from what it knows, never a sentence about "her library" said to him as the answer. And "what should I plant
in the spring?", which the model had answered from nothing, is what's due from his frost.
"""

from types import SimpleNamespace

from core import offline_library


def test_no_packs_tells_the_model_to_answer_from_what_it_knows():
    said = offline_library.look_up(SimpleNamespace(list_packs=lambda: []), "how much space do goats need?")
    assert "Answer from what you know" in said and "Her offline library" not in said


def test_what_to_plant_now_is_from_his_frost(monkeypatch):
    from core import assistant_turn, planting_now

    monkeypatch.setattr(planting_now, "say_now", lambda c: "what's due")
    for words in ("What should I plant in the spring?", "what can I plant now", "what should I grow this month?"):
        assert assistant_turn._garden_kit_reply(None, words) == "what's due", words
    assert assistant_turn._garden_kit_reply(None, "what should I plant to attract bees?") is None
