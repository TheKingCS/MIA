"""What a conversation is about (DEC-0052 step 4, core/conversation_state.py):
a short follow-up goes back to the last question plan, with both questions."""

from types import SimpleNamespace

import pytest

import core.meaning as meaning
from core import conversation_state as cs
from core import question_plans as qp
from tests.test_crafting import shop  # noqa: F401  (the fixture)


def test_what_reads_as_a_follow_up():
    for said in ("why?", "What about last month?", "and the truck?", "what if I paid $300 more?", "tell me more",
                 "is that a lot?", "How much is that?"):
        assert cs.looks_like_follow_up(said), said
    for said in ("Which debt should I prioritize?", "Add milk to the grocery list",
                 "What did I spend on groceries over the last three months compared to my budget?"):
        assert not cs.looks_like_follow_up(said), said


@pytest.fixture
def life(shop, monkeypatch):  # noqa: F811
    from tests.assistant_registry import build_desktop_registry

    shop.assistant_actions = build_desktop_registry()
    monkeypatch.setattr(meaning, "nearest", lambda *a, **k: None)
    return shop


def test_a_follow_up_goes_back_to_the_same_plan(life):
    life.budget.add_debt(name="Card", balance=3000, interest_rate=20, minimum_payment=90)
    talk = SimpleNamespace(conversation_id="c1", messages=[], mode=None)
    first = qp.request(life, talk, "Which debt should I prioritize?")
    assert first is not None and first[1].plan == "debts"
    messages, sheet = qp.request(life, talk, "what if I paid $300 more?")
    assert sheet.plan == "debts" and "$300.00 more a month to Card first" in sheet.as_text()
    other = SimpleNamespace(conversation_id="c2", messages=[], mode=None)
    assert qp.request(life, other, "why?") is None  # another conversation knows nothing of it
    cs.forget(talk)
    assert qp.request(life, talk, "why?") is None


def test_a_follow_up_naming_another_plan_changes_the_subject(life, monkeypatch):
    talk = SimpleNamespace(conversation_id="c3", messages=[], mode=None)
    assert qp.request(life, talk, "What's coming up in the next few weeks?")[1].plan == "coming up"
    assert qp.request(life, talk, "and what about tonight?")[1].plan == "tonight"  # "tonight": that plan's own word
    assert qp.request(life, talk, "why?")[1].plan == "tonight"  # and now the follow-ups are about tonight


def test_the_desktop_gets_the_same_instant_answers(life):
    """The desktop's chat panels build their own request; instant_answer gives
    them what the web and phone already had: code answers, plan questions
    left to the plan, nothing in a personal mode."""
    from core.assistant_turn import instant_answer

    talk = SimpleNamespace(conversation_id="d1", messages=[], mode=None, journal=False)
    said = instant_answer(life, talk, "What are you capable of?")
    assert said is not None and said.startswith("I have ")
    assert instant_answer(life, talk, "Which debt should I prioritize?") is None  # the debts plan answers
    assert instant_answer(life, talk, "Tell me a joke.") is None  # for the model
    listening = SimpleNamespace(conversation_id="d2", messages=[], mode="listen", journal=False)
    assert instant_answer(life, listening, "What are you capable of?") is None
