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
