"""
tests.test_assistant_chat
=============================

Unit tests for core.assistant_chat's pure logic — format_chat_line,
looks_like_action_request, build_chat_request, and split_safe_tool_calls
— no Qt event loop needed. Moved here from tests/test_assistant_module.py
(2026-07-14 aesthetic pass part 4) alongside the functions themselves
moving from modules/assistant/module.py to core/assistant_chat.py — see
that module's docstring for why. Same shape as tests/test_notes_module.py's
format_entry_row test: the widget-building and worker-thread wiring in
AssistantModule/the sidebar chat needs a real Qt event loop to exercise
meaningfully, so that was verified with a manual headless smoke test
instead (offscreen QPA platform) rather than unit-tested here.
"""

from __future__ import annotations

from core.assistant_chat import (
    DOMAIN_EXAMPLE_PROMPTS,
    build_chat_request,
    format_chat_line,
    looks_like_action_request,
    split_safe_tool_calls,
    suggested_prompts_for_module,
)
from core.llm_manager import ToolCall


def test_formats_speaker_and_text():
    assert format_chat_line("You", "hello") == "You: hello"


def test_formats_assistant_reply():
    assert format_chat_line("Assistant", "hi there") == "Assistant: hi there"


# ----------------------------------------------------------------------
# looks_like_action_request
# ----------------------------------------------------------------------
# Regression coverage for a real-usage bug: asking "What can you tell me
# about Honda Civics?" made the model hallucinate a nonexistent
# module_id and call open_module instead of answering "I don't know" —
# traced to tools being attached to every message unconditionally, even
# pure information questions with no relevant action. See
# modules/assistant/module.py's docstring and looks_like_action_request()'s
# docstring.

def test_honda_civics_question_is_not_an_action_request():
    assert looks_like_action_request("What can you tell me about Honda Civics?") is False


def test_plain_information_question_is_not_an_action_request():
    assert looks_like_action_request("What are the symptoms of hypothermia?") is False


def test_open_module_phrasing_is_an_action_request():
    assert looks_like_action_request("Open the notes module for me") is True


def test_set_an_alarm_phrasing_is_an_action_request():
    assert looks_like_action_request("Set an alarm called Wake Up for 07:00") is True


def test_remind_me_phrasing_is_an_action_request():
    assert looks_like_action_request("Remind me to take out the trash") is True


def test_add_a_note_phrasing_is_an_action_request():
    assert looks_like_action_request("Add a note that says buy milk") is True


def test_add_to_inventory_phrasing_is_an_action_request():
    assert looks_like_action_request("Add to inventory: 10 M3 bolts") is True


def test_recent_activity_phrasing_is_an_action_request():
    assert looks_like_action_request("What have I been doing recently?") is True


def test_notebook_word_does_not_false_positive_on_note_keyword():
    """Loose "note" would false-positive on unrelated words like "notebook" — must require the fuller phrase."""
    assert looks_like_action_request("What's a good notebook for taking handwritten notes?") is False


# ----------------------------------------------------------------------
# build_chat_request
# ----------------------------------------------------------------------
# Extracted out of _on_send() so tests/live_model_check.py's golden-set
# regression script exercises this exact logic against the real Ollama
# server, not a hand-copied reimplementation — see this function's
# docstring.

class _FakeAssistantActions:
    """
    Stands in for the real AssistantActionRegistry's domain-scoped
    matching_actions()/to_ollama_tools(actions) pair (core/assistant_actions.py) —
    `_tools` itself doubles as the "matched actions" list here since
    build_chat_request() just threads whatever matching_actions()
    returns straight into to_ollama_tools(), and this fake never needs
    real AssistantAction objects or domain grouping to exercise that
    plumbing.
    """

    def __init__(self, keywords, tools):
        self._keywords = keywords
        self._tools = tools

    def matching_actions(self, prompt):
        lowered = f" {prompt.lower().strip()} "
        if any(keyword in lowered for keyword in self._keywords):
            return self._tools
        return []

    def to_ollama_tools(self, actions=None):
        return actions if actions is not None else self._tools


class _FakeDeviceHelp:
    def build_grounded_prompt(self, prompt):
        return f"GROUNDED[{prompt}]"


class _FakeContext:
    def __init__(self, assistant_actions=None, device_help=None):
        self.assistant_actions = assistant_actions
        self.device_help = device_help


def test_build_chat_request_action_prompt_uses_raw_prompt_and_tools():
    context = _FakeContext(
        assistant_actions=_FakeAssistantActions(keywords=["open "], tools=[{"type": "function"}]),
        device_help=_FakeDeviceHelp(),
    )
    messages, tools = build_chat_request(context, "Open the notes module")
    assert messages == [{"role": "user", "content": "Open the notes module"}]
    assert tools == [{"type": "function"}]


def test_build_chat_request_info_prompt_uses_grounding_and_no_tools():
    context = _FakeContext(
        assistant_actions=_FakeAssistantActions(keywords=["open "], tools=[{"type": "function"}]),
        device_help=_FakeDeviceHelp(),
    )
    messages, tools = build_chat_request(context, "What are the symptoms of hypothermia?")
    assert messages == [{"role": "user", "content": "GROUNDED[What are the symptoms of hypothermia?]"}]
    assert tools == []


def test_build_chat_request_without_device_help_uses_raw_prompt_for_info_questions():
    context = _FakeContext(assistant_actions=_FakeAssistantActions(keywords=[], tools=[]), device_help=None)
    messages, tools = build_chat_request(context, "What are the symptoms of hypothermia?")
    assert messages == [{"role": "user", "content": "What are the symptoms of hypothermia?"}]
    assert tools == []


def test_build_chat_request_without_assistant_actions_never_offers_tools():
    context = _FakeContext(assistant_actions=None, device_help=_FakeDeviceHelp())
    messages, tools = build_chat_request(context, "Open the notes module")
    assert messages == [{"role": "user", "content": "GROUNDED[Open the notes module]"}]
    assert tools == []


# ----------------------------------------------------------------------
# split_safe_tool_calls — 2026-07-14 qwen2.5:7b model-comparison finding
# ----------------------------------------------------------------------

class _FakeDestructiveLookup:
    def __init__(self, destructive_names):
        self._destructive_names = set(destructive_names)

    def is_destructive(self, name):
        return name in self._destructive_names


def test_split_safe_tool_calls_single_call_executes_even_if_destructive():
    calls = [ToolCall(name="delete_alarm", arguments={"label": "Wake Up"})]
    registry = _FakeDestructiveLookup({"delete_alarm"})

    kept, skipped = split_safe_tool_calls(calls, registry)

    assert kept == calls
    assert skipped == []


def test_split_safe_tool_calls_no_calls():
    kept, skipped = split_safe_tool_calls([], _FakeDestructiveLookup({}))
    assert kept == []
    assert skipped == []


def test_split_safe_tool_calls_multiple_calls_skips_the_destructive_one():
    """
    Reproduces the exact 2026-07-14 qwen2.5:7b finding: "How many M3
    bolts do I have?" returned both list_inventory (safe) and a
    spurious adjust_inventory_quantity (destructive) in one reply.
    """
    read_call = ToolCall(name="list_inventory", arguments={"query": "M3 bolts"})
    destructive_call = ToolCall(name="adjust_inventory_quantity", arguments={"name": "M3 bolts", "delta": -1})
    registry = _FakeDestructiveLookup({"adjust_inventory_quantity"})

    kept, skipped = split_safe_tool_calls([destructive_call, read_call], registry)

    assert kept == [read_call]
    assert skipped == [destructive_call]


def test_split_safe_tool_calls_multiple_non_destructive_calls_all_kept():
    calls = [
        ToolCall(name="list_alarms", arguments={}),
        ToolCall(name="list_notes", arguments={}),
    ]
    registry = _FakeDestructiveLookup({"delete_alarm"})  # neither call is in this set

    kept, skipped = split_safe_tool_calls(calls, registry)

    assert kept == calls
    assert skipped == []


def test_split_safe_tool_calls_multiple_destructive_calls_all_skipped():
    calls = [
        ToolCall(name="delete_alarm", arguments={"label": "Wake Up"}),
        ToolCall(name="delete_note", arguments={"title": "Groceries"}),
    ]
    registry = _FakeDestructiveLookup({"delete_alarm", "delete_note"})

    kept, skipped = split_safe_tool_calls(calls, registry)

    assert kept == []
    assert skipped == calls


# ----------------------------------------------------------------------
# suggested_prompts_for_module
# ----------------------------------------------------------------------

def test_suggested_prompts_for_home_screen_uses_generic_set():
    prompts = suggested_prompts_for_module(None)
    assert prompts
    assert len(prompts) <= 4


def test_suggested_prompts_for_unmapped_module_uses_generic_set():
    assert suggested_prompts_for_module("music") == suggested_prompts_for_module(None)


def test_suggested_prompts_for_single_domain_module():
    prompts = suggested_prompts_for_module("missions")
    assert prompts == DOMAIN_EXAMPLE_PROMPTS["missions"]


def test_suggested_prompts_for_multi_domain_module_spreads_across_domains():
    """Toolbox spans 4 domains — the first round should draw one prompt from each, not four from one."""
    prompts = suggested_prompts_for_module("toolbox")
    assert len(prompts) == 4
    assert prompts == [
        DOMAIN_EXAMPLE_PROMPTS["alarms"][0],
        DOMAIN_EXAMPLE_PROMPTS["calendar"][0],
        DOMAIN_EXAMPLE_PROMPTS["inventory"][0],
        DOMAIN_EXAMPLE_PROMPTS["projects"][0],
    ]


def test_suggested_prompts_never_exceeds_limit_of_four():
    for module_id in ["missions", "expeditions", "toolbox", "field_kit", None, "some_unknown_module"]:
        assert len(suggested_prompts_for_module(module_id)) <= 4
