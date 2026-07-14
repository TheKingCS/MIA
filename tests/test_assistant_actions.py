"""
tests.test_assistant_actions
===============================

Unit tests for core.assistant_actions.AssistantActionRegistry. No LLM
or Ollama involved — these test the registry's own execute()/
to_ollama_tools() logic directly with fake handlers.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry


def _make_action(name="test_action", handler=None) -> AssistantAction:
    return AssistantAction(
        name=name,
        description="A test action.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=handler or (lambda context, arguments: "done"),
    )


def test_execute_calls_the_registered_handler():
    seen = {}

    def handler(context, arguments):
        seen["context"] = context
        seen["arguments"] = arguments
        return "handled"

    registry = AssistantActionRegistry()
    registry.register(_make_action(handler=handler))

    result = registry.execute("fake-context", "test_action", {"x": 1})

    assert result == "handled"
    assert seen["context"] == "fake-context"
    assert seen["arguments"] == {"x": 1}


def test_execute_unknown_action_returns_message_not_raise():
    registry = AssistantActionRegistry()
    result = registry.execute("fake-context", "does_not_exist", {})
    assert "does_not_exist" in result


def test_execute_handler_exception_returns_message_not_raise():
    def broken_handler(context, arguments):
        raise RuntimeError("boom")

    registry = AssistantActionRegistry()
    registry.register(_make_action(handler=broken_handler))

    result = registry.execute("fake-context", "test_action", {})
    assert "test_action" in result


def test_to_ollama_tools_shape():
    registry = AssistantActionRegistry()
    registry.register(AssistantAction(
        name="add_alarm",
        description="Create a new alarm.",
        parameters={"type": "object", "properties": {"label": {"type": "string"}}, "required": ["label"]},
        handler=lambda context, arguments: "ok",
    ))

    tools = registry.to_ollama_tools()
    assert tools == [{
        "type": "function",
        "function": {
            "name": "add_alarm",
            "description": "Create a new alarm.",
            "parameters": {"type": "object", "properties": {"label": {"type": "string"}}, "required": ["label"]},
        },
    }]


def test_to_ollama_tools_empty_registry():
    registry = AssistantActionRegistry()
    assert registry.to_ollama_tools() == []


# ----------------------------------------------------------------------
# gating_keywords — milestone 5.9
# ----------------------------------------------------------------------

def test_gating_keywords_flattens_all_registered_actions():
    registry = AssistantActionRegistry()
    registry.register(AssistantAction(
        name="a",
        description="A.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda context, arguments: "ok",
        trigger_phrases=("open ", "launch "),
    ))
    registry.register(AssistantAction(
        name="b",
        description="B.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda context, arguments: "ok",
        trigger_phrases=("set an alarm",),
    ))

    assert registry.gating_keywords() == ["open ", "launch ", "set an alarm"]


def test_gating_keywords_empty_when_no_trigger_phrases():
    registry = AssistantActionRegistry()
    registry.register(_make_action())
    assert registry.gating_keywords() == []

# ----------------------------------------------------------------------
# matching_actions — domain-scoped tool attachment
# ----------------------------------------------------------------------

def _register_domain_fixture(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="add_alarm", description="Create a new alarm.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda context, arguments: "ok",
        trigger_phrases=("set an alarm",), domain="alarms",
    ))
    registry.register(AssistantAction(
        name="list_alarms", description="List alarms.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda context, arguments: "ok",
        trigger_phrases=("list my alarms",), domain="alarms",
    ))
    registry.register(AssistantAction(
        name="calculate_subnet", description="Calculate a subnet.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda context, arguments: "ok",
        trigger_phrases=("calculate subnet",), domain="security",
    ))
    registry.register(AssistantAction(
        name="open_module", description="Open a module.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda context, arguments: "ok",
        trigger_phrases=("switch to ",), domain="system",
    ))
    registry.register(AssistantAction(
        name="get_system_health", description="Report system health.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda context, arguments: "ok",
        trigger_phrases=("system health",), domain="system",
    ))


def test_matching_actions_returns_empty_when_nothing_matches():
    registry = AssistantActionRegistry()
    _register_domain_fixture(registry)
    assert registry.matching_actions("What can you tell me about Honda Civics?") == []


def test_matching_actions_attaches_only_matched_domain_plus_always_on():
    registry = AssistantActionRegistry()
    _register_domain_fixture(registry)

    matched = {a.name for a in registry.matching_actions("Set an alarm for 7am")}
    # Both alarm-domain actions (list_alarms' own trigger didn't match,
    # but it shares add_alarm's domain) plus the always-on system
    # domain — never the unrelated security-domain calculate_subnet.
    assert matched == {"add_alarm", "list_alarms", "open_module", "get_system_health"}
    assert "calculate_subnet" not in matched


def test_matching_actions_never_includes_an_unrelated_domain():
    registry = AssistantActionRegistry()
    _register_domain_fixture(registry)

    matched = {a.name for a in registry.matching_actions("Calculate subnet 192.168.1.0/24")}
    assert "add_alarm" not in matched
    assert "list_alarms" not in matched
    assert "calculate_subnet" in matched


def test_matching_actions_always_includes_the_system_domain_when_any_domain_matches():
    registry = AssistantActionRegistry()
    _register_domain_fixture(registry)

    matched = {a.name for a in registry.matching_actions("List my alarms")}
    assert "open_module" in matched
    assert "get_system_health" in matched


def test_matching_actions_unions_multiple_matched_domains():
    registry = AssistantActionRegistry()
    _register_domain_fixture(registry)

    matched = {a.name for a in registry.matching_actions("Set an alarm and calculate subnet 10.0.0.0/8")}
    assert "add_alarm" in matched
    assert "calculate_subnet" in matched


def test_to_ollama_tools_accepts_an_explicit_actions_subset():
    registry = AssistantActionRegistry()
    _register_domain_fixture(registry)

    subset = [a for a in registry.matching_actions("List my alarms") if a.name == "add_alarm"]
    tools = registry.to_ollama_tools(subset)
    assert [t["function"]["name"] for t in tools] == ["add_alarm"]

# ----------------------------------------------------------------------
# destructive — 2026-07-14 qwen2.5:7b model-comparison finding
# ----------------------------------------------------------------------

def test_is_destructive_true_for_a_destructive_action():
    registry = AssistantActionRegistry()
    registry.register(AssistantAction(
        name="delete_alarm", description="Delete an alarm.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda context, arguments: "ok",
        destructive=True,
    ))
    assert registry.is_destructive("delete_alarm") is True


def test_is_destructive_false_by_default():
    registry = AssistantActionRegistry()
    registry.register(_make_action(name="list_alarms"))
    assert registry.is_destructive("list_alarms") is False


def test_is_destructive_false_for_unknown_name():
    registry = AssistantActionRegistry()
    assert registry.is_destructive("does_not_exist") is False


def test_destructive_action_names_returns_only_flagged_actions():
    registry = AssistantActionRegistry()
    registry.register(AssistantAction(
        name="delete_alarm", description="Delete an alarm.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda context, arguments: "ok",
        destructive=True,
    ))
    registry.register(_make_action(name="list_alarms"))

    assert registry.destructive_action_names() == {"delete_alarm"}
