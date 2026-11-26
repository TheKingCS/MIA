"""
tests.test_sweep_26
=====================

The full live sweep of 2026-11-26: "we're out of milk" goes to the grocery list in code (it had been added to the
pantry); a problem he describes never marks a job done (a squealing truck had reached complete_maintenance_task);
the model writing out its own lookup ("Tool call: ... Response: ...") keeps only the answer; "do you remember what I
told you yesterday?" reads her record of it.
"""

from types import SimpleNamespace

from core import assistant_turn, response_composer, tool_loop
from core.llm_manager import ChatReply, ToolCall


def _actions(ran):
    return SimpleNamespace(execute=lambda c, name, args: ran.append((name, args)) or "done")


def test_out_of_milk_goes_to_the_grocery_list():
    ran = []
    context = SimpleNamespace(assistant_actions=_actions(ran))
    assert assistant_turn._own_tool_reply(context, "We're out of milk") == "done"
    assert ran[-1] == ("add_grocery_item", {"items": "milk", "question": "We're out of milk"})
    for words in ("I'm out of time", "we're out of gas", "I'm all out of ideas"):
        ran.clear()
        assistant_turn._own_tool_reply(context, words)
        assert not ran or ran[-1][0] != "add_grocery_item", words


def test_remembering_yesterday_reads_her_record():
    ran = []
    context = SimpleNamespace(assistant_actions=_actions(ran))
    for words in ("Do you remember what I told you yesterday?", "what did we talk about yesterday"):
        assert assistant_turn._own_tool_reply(context, words) == "done", words
        assert ran[-1][0] == "list_past_conversations"


def test_a_problem_described_is_never_a_job_done():
    marked = ChatReply(content="", tool_calls=[ToolCall(name="complete_maintenance_task", arguments={"title": "it"})])
    assert tool_loop.tells_trouble("My truck has been making a squealing noise when I brake", marked)
    assert tool_loop.tells_trouble("the furnace won't start", marked)
    assert not tool_loop.tells_trouble("I changed the brakes, they were squealing", marked)
    added = ChatReply(content="", tool_calls=[ToolCall(name="add_maintenance_task", arguments={})])
    assert not tool_loop.tells_trouble("My truck has been making a squealing noise", added)


def test_a_written_out_lookup_keeps_only_the_answer():
    said = response_composer.polish('Tool call: "What is the best breed of goat for milk?"\n\nResponse: "Nubians and '
                                    'Nigerian Dwarfs are the usual milk breeds."')
    assert said == "Nubians and Nigerian Dwarfs are the usual milk breeds."
