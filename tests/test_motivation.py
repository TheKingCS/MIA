"""
tests.test_motivation
=======================

"I need motivation" (core/motivation.py, the full sweep 2026-11-26): his own reasons said back and one small thing
from today, never a guess about how he feels.
"""

from types import SimpleNamespace

from core import assistant_turn, motivation


def test_his_reasons_and_one_small_step(monkeypatch):
    from core import today, why_graph

    chain = [SimpleNamespace(name="Factory work", done=False), SimpleNamespace(name="Pay off debt", done=False),
             SimpleNamespace(name="Control over my time", done=False)]
    monkeypatch.setattr(why_graph, "build_why_sheet", lambda c, **k: SimpleNamespace(is_empty=False, chains=[chain]))
    item = SimpleNamespace(title="Sharpen the mower blades", module_id="maintenance", when="today",
                           as_dict=lambda: {"detail": ""})
    monkeypatch.setattr(today, "today_items", lambda c, t=None: [item])
    said = motivation.say(SimpleNamespace(intents=object()))
    assert said.startswith("Here's what you told me you're working toward: Factory work → Pay off debt → Control")
    assert "One small thing to start with: Sharpen the mower blades." in said


def test_with_no_reasons_it_asks_for_one(monkeypatch):
    from core import today

    monkeypatch.setattr(today, "today_items", lambda c, t=None: [])
    assert motivation.say(SimpleNamespace()).startswith("Tell me what you're working toward and why")


def test_the_words_reach_it(monkeypatch):
    monkeypatch.setattr(motivation, "say", lambda c, t=None, task="": "why")
    for words in ("I need motivation", "motivate me", "I'm so unmotivated today"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "why", words
