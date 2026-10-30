"""The tool loop (DEC-0052 step 2b, core/tool_loop.py): lookups go back to
the model and it may look up more, a few rounds at most, never the same
lookup twice; one answer at the end that never states a number the
lookups didn't; a change is never run inside the loop."""

from types import SimpleNamespace

import pytest

import core.tool_loop as tool_loop
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.llm_manager import ChatReply, ToolCall


def _action(name, said):
    return AssistantAction(name=name, domain="money", description=name, parameters={"type": "object", "properties": {}},
                           handler=lambda context, arguments: said, trigger_phrases=(name,))


@pytest.fixture
def life(monkeypatch):
    registry = AssistantActionRegistry()
    registry.register(_action("list_bills", "Electric $80.00 due Friday."))
    registry.register(_action("get_budget_summary", "Income: $2,000.00. Expenses: $1,500.00."))
    registry.register(_action("add_bill", "Added."))
    monkeypatch.setattr(tool_loop, "loop_ok", lambda context: True)
    return SimpleNamespace(assistant_actions=registry, config=None)


class _Model:
    """Replies in order; remembers what it was sent."""

    def __init__(self, *replies):
        self.replies, self.sent = list(replies), []

    def chat_with_tools(self, messages, tools):
        self.sent.append((messages, tools))
        return self.replies.pop(0)


def call(*names):
    return ChatReply(content="", tool_calls=[ToolCall(name=n, arguments={}) for n in names])


TOOLS = [{"function": {"name": "list_bills"}}]


def test_lookups_go_back_and_one_answer_comes_out(life):
    model = _Model(call("list_bills"), call("get_budget_summary"),
                   ChatReply(content="Yes: the $80.00 electric bill is due Friday, and $2,000.00 came in.", tool_calls=[]))
    reply = tool_loop.run(life, model, [{"role": "user", "content": "can I cover my bills?"}], TOOLS, "can I cover my bills?")
    assert reply.tool_calls == [] and reply.content.startswith("Yes: the $80.00")
    second = model.sent[1][0]
    assert any(m.get("role") == "tool" and m["content"].startswith("Electric") for m in second)


def test_an_invented_number_gets_one_retry_then_the_results(life):
    said_twice = ChatReply(content="You owe $95 this week.", tool_calls=[])
    model = _Model(call("list_bills"), said_twice, said_twice)
    reply = tool_loop.run(life, model, [], TOOLS, "what bills do I have?")
    assert reply.content == "Electric $80.00 due Friday."
    assert "aren't in their records: 95" in model.sent[-1][0][-1]["content"]  # told which number, once
    # Arithmetic is code's job, so the model's own sum is refused too ($2,000 - $1,500 is never on a result).
    no_sum = ChatReply(content="You have $500.00 left.", tool_calls=[])
    model = _Model(call("get_budget_summary"), no_sum, no_sum)
    assert tool_loop.run(life, model, [], TOOLS, "q").content == "Income: $2,000.00. Expenses: $1,500.00."


def test_a_retry_without_the_number_is_kept(life):
    model = _Model(call("list_bills"), ChatReply(content="Electric is due Friday; most bills run every 30 days.", tool_calls=[]),
                   ChatReply(content="Electric is $80.00, due Friday.", tool_calls=[]))
    assert tool_loop.run(life, model, [], TOOLS, "bills?").content == "Electric is $80.00, due Friday."


def test_the_same_lookup_twice_stops_the_loop(life):
    model = _Model(call("list_bills"), call("list_bills"))
    reply = tool_loop.run(life, model, [], TOOLS, "bills?")
    assert reply.content == "Electric $80.00 due Friday." and len(model.sent) == 2


def test_rounds_are_limited_and_the_last_has_no_tools(life):
    model = _Model(call("list_bills"), call("get_budget_summary"), call("list_bills", "get_budget_summary"),
                   ChatReply(content="Done looking.", tool_calls=[]))
    tool_loop.run(life, model, [], TOOLS, "q", budget=60)
    # a fresh pair would be a 3rd round, but list_bills + summary were both seen: the loop stops after round 2
    assert len(model.sent) == 3
    model = _Model(call("get_budget_summary"), ChatReply(content="Answer.", tool_calls=[]))
    reply = tool_loop.run(life, model, [], TOOLS, "q", budget=-1)  # out of time: the first round still runs
    assert reply.content == "Answer." and model.sent[-1][1] == []  # then the last word, with no tools


def test_a_change_is_never_run_inside_the_loop(life):
    model = _Model(call("add_bill"))
    reply = tool_loop.run(life, model, [], TOOLS, "add my water bill")
    assert [c.name for c in reply.tool_calls] == ["add_bill"] and len(model.sent) == 1
    model = _Model(call("list_bills"), call("add_bill"))
    reply = tool_loop.run(life, model, [], TOOLS, "q")
    assert [c.name for c in reply.tool_calls] == ["add_bill"]  # back to the caller's usual path


def test_without_this_computers_ollama_nothing_changes(life, monkeypatch):
    monkeypatch.setattr(tool_loop, "loop_ok", lambda context: False)
    model = _Model(call("list_bills"))
    reply = tool_loop.run(life, model, [], TOOLS, "q")
    assert [c.name for c in reply.tool_calls] == ["list_bills"] and len(model.sent) == 1


def test_a_question_never_makes_a_change_nobody_asked_for(life):
    """The benchmark: "What lessons have I learned?" reached for add_course."""
    model = _Model(call("add_bill"), ChatReply(content="No lessons are recorded yet. Want me to start a list?", tool_calls=[]))
    reply = tool_loop.run(life, model, [], TOOLS, "What lessons have I learned from previous experiences?")
    assert reply.tool_calls == [] and reply.content.startswith("No lessons")
    assert all(t["function"]["name"] != "add_bill" for t in model.sent[1][1])  # the retry offered lookups only
    asked = _Model(call("add_bill"))
    for request in ("can you add my water bill?", "add my water bill"):
        asked.replies = [call("add_bill")]
        assert [c.name for c in tool_loop.run(life, asked, [], TOOLS, request).tool_calls] == ["add_bill"], request


def test_asks_not_tells():
    assert tool_loop.asks_not_tells("What lessons have I learned?")
    assert tool_loop.asks_not_tells("Is it more profitable to make products to order or keep inventory?")
    assert not tool_loop.asks_not_tells("Can you add milk to the list?")
    assert not tool_loop.asks_not_tells("Add milk to the list")
    assert not tool_loop.asks_not_tells("I spent 40 on gas")


def test_after_looking_a_question_still_gets_an_answer_not_a_change(life):
    model = _Model(call("list_bills"), call("add_bill"), ChatReply(content="Electric $80.00 is due Friday.", tool_calls=[]))
    reply = tool_loop.run(life, model, [], TOOLS, "What bills do I have?")
    assert reply.tool_calls == [] and reply.content == "Electric $80.00 is due Friday." and model.sent[-1][1] == []
