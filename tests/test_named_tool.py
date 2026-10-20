"""
The tool a message names in its own words (2026-10-19, the PC model's
misses): AssistantActionRegistry.named_action() and
core/assistant_chat.settle_on_named_tool(). Pure logic, no model.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_chat import settle_on_named_tool
from core.llm_manager import ChatReply, ToolCall


def _registry() -> AssistantActionRegistry:
    registry = AssistantActionRegistry()

    def add(name, phrases, required=(), destructive=False, subjects=()):
        registry.register(AssistantAction(
            name=name, description="", handler=lambda c, a: "", trigger_phrases=phrases, destructive=destructive,
            subjects=subjects, parameters={"type": "object", "properties": {k: {"type": "string"} for k in required},
                                           "required": list(required)}))

    add("add_note", ("add a note",), required=("title",))
    add("add_recipe", ("add a recipe", "recipe for"), required=("name",))
    add("list_recipes", ("my recipes",))
    add("get_debt_payoff_plan", ("which debt", "pay off first"))
    add("list_debts", ("my debts",))
    add("list_inventory", ("do i have", "inventory"))
    add("delete_inventory_item", ("remove from inventory",), destructive=True)
    add("list_household_routines", ("what chores",), subjects=("chore",))
    return registry


ALL = ["add_note", "add_recipe", "list_recipes", "get_debt_payoff_plan", "list_debts", "list_inventory",
       "delete_inventory_item", "list_household_routines"]


def test_names_the_one_tool_the_message_asks_for():
    registry = _registry()
    assert registry.named_action("Add a note that says buy milk", ALL) == "add_note"
    assert registry.named_action("Can you add a recipe for garden salsa", ALL) == "add_recipe"
    assert registry.named_action("Which debt should I pay off first?", ALL) == "get_debt_payoff_plan"
    assert registry.named_action("What chores are left today?", ALL) == "list_household_routines"


def test_never_names_a_change_the_message_only_mentions():
    registry = _registry()
    assert registry.named_action("Do I have a recipe for chili?", ALL) is None
    assert registry.named_action("Find me a recipe for chili", ALL) is None


def test_a_lookup_needs_a_question_that_names_its_subject():
    registry = _registry()
    assert registry.named_action("What user profiles do I have set up?", ALL) is None  # "do i have" alone
    assert registry.named_action("Remove the bolts from inventory", ALL) is None  # not a question


def test_only_offered_tools_count():
    assert _registry().named_action("Add a note that says buy milk", ["list_recipes"]) is None


def _tools(*names):
    return [{"type": "function", "function": {"name": n, "parameters": {
        "type": "object", "properties": {}, "required": ["title"] if n == "add_note" else []}}} for n in names]


def _reply(*calls, content=""):
    return ChatReply(content=content, tool_calls=[ToolCall(name=n, arguments=a) for n, a in calls])


def _never(messages, tools):
    raise AssertionError("asked the model again")


def test_keeps_a_reply_that_already_called_it():
    reply = _reply(("add_note", {"title": "buy milk"}))
    assert settle_on_named_tool("add_note", [], _tools("add_note"), reply, _never) is reply


def test_keeps_just_the_named_call_from_several():
    reply = _reply(("get_business_use", {}), ("get_maintenance_asset", {}))
    settled = settle_on_named_tool("get_business_use", [], _tools("get_business_use"), reply, _never)
    assert [c.name for c in settled.tool_calls] == ["get_business_use"]


def test_asks_again_with_only_that_tool_when_the_model_asked_back():
    asked = []

    def ask(messages, tools):
        asked.append((messages, tools))
        return _reply(("add_note", {"title": "buy milk"}))

    reply = _reply(content="What should the title be?")
    settled = settle_on_named_tool("add_note", [{"role": "user", "content": "x"}], _tools("add_note", "list_notes"),
                                   reply, ask)
    assert [c.name for c in settled.tool_calls] == ["add_note"]
    assert [t["function"]["name"] for t in asked[0][1]] == ["add_note"]
    assert asked[0][0][-1]["role"] == "system"


def test_asks_again_when_the_model_picked_another_lookup():
    reply = _reply(("list_debts", {}))
    settled = settle_on_named_tool("get_debt_payoff_plan", [], _tools("list_debts", "get_debt_payoff_plan"), reply,
                                   lambda m, t: _reply(("get_debt_payoff_plan", {})))
    assert [c.name for c in settled.tool_calls] == ["get_debt_payoff_plan"]


def test_a_change_the_model_chose_stays():
    reply = _reply(("add_maintenance_task", {}))
    assert settle_on_named_tool("add_alarm", [], _tools("add_alarm"), reply, _never) is reply


def test_keeps_the_first_reply_when_the_second_try_misses_a_required_detail():
    reply = _reply(content="What should it say?")
    settled = settle_on_named_tool("add_note", [], _tools("add_note"), reply, lambda m, t: _reply(("add_note", {"title": " "})))
    assert settled is reply
    assert settle_on_named_tool("add_note", [], _tools("add_note"), reply, lambda m, t: None) is reply


def test_nothing_named_changes_nothing():
    reply = _reply(content="hi")
    assert settle_on_named_tool(None, [], _tools("add_note"), reply, _never) is reply
    assert settle_on_named_tool("add_note", [], _tools("add_note"), None, _never) is None
