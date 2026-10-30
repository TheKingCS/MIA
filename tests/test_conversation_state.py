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


def test_what_fell_out_of_the_window_is_still_known():
    said = [SimpleNamespace(role=r, content=c) for r, c in (
        ("user", "How's the truck?"), ("assistant", "Oil change is due."),
        ("user", "And the mower?"), ("assistant", "Blades next week."),
        ("user", "What's for dinner?"), ("assistant", "Chili."))]
    assert cs.earlier_topics(said, 2) == ("Earlier in this conversation (older than the messages below) they asked: "
                                          "“How's the truck?”; “And the mower?”.")
    assert cs.earlier_topics(said, 6) == ""  # nothing was cut


def test_the_model_is_told_what_came_earlier(life):
    from core.assistant_chat import build_chat_request

    talk = SimpleNamespace(conversation_id="w1", mode=None, journal=False, messages=[
        SimpleNamespace(role="user" if i % 2 == 0 else "assistant", content=f"message {i}") for i in range(20)])
    messages, _tools = build_chat_request(life, talk, "Tell me a story")
    system = messages[0]["content"]  # the last 12 are shown; 0 to 7 were cut, and their questions are named
    assert "they asked: “message 0”; “message 2”; “message 4”; “message 6”." in system
    assert "“message 8”" not in system  # still in the window, so not repeated


def test_what_it_means(life):
    from core.assistant_chat import build_chat_request

    truck = life.maintenance.add_asset("Pickup Truck", "Vehicle")
    life.maintenance.add_task(truck.asset_id, "Oil change", interval_days=90)
    life.maintenance.add_asset("Riding Mower", "Power Equipment")
    talk = SimpleNamespace(conversation_id="i1", mode=None, journal=False, messages=[
        SimpleNamespace(role="user", content="How's the truck doing?"),
        SimpleNamespace(role="assistant", content="The Pickup Truck's oil change is due in 12 days.")])
    assert cs.what_it_means(life, talk, "when did I last change it?") == "Pickup Truck"
    assert cs.what_it_means(life, talk, "when did I last service the mower?") is None  # names its own subject
    assert cs.what_it_means(life, talk, "What's for dinner?") is None  # leans on nothing
    assert cs.what_it_means(life, talk, "That's cool.") is None  # small talk, not about a record
    assert cs.what_it_means(life, talk, "move it to Saturday") == "Pickup Truck"  # a request about it
    messages, tools = build_chat_request(life, talk, "when did I last change it?")
    assert "most likely means Pickup Truck" in messages[0]["content"]
    assert "list_maintenance_tasks" in [t["function"]["name"] for t in tools]  # the truck's tools came along
    both = SimpleNamespace(conversation_id="i2", mode=None, journal=False, messages=[
        SimpleNamespace(role="user", content="Compare the truck and the mower")])
    assert cs.what_it_means(life, both, "which needs it more?") is None  # two things: too unsure
