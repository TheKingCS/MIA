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
    build_memory_extraction_prompt,
    build_system_message,
    build_title_generation_prompt,
    build_user_context_block,
    clean_generated_title,
    format_birthday,
    format_chat_line,
    looks_like_action_request,
    parse_extracted_memories,
    split_safe_tool_calls,
    suggested_prompts_for_module,
    trim_history,
)
from core.conversation_manager import Conversation, ConversationMessage
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
    def __init__(self, assistant_actions=None, device_help=None, profiles=None, user_memories=None):
        self.assistant_actions = assistant_actions
        self.device_help = device_help
        self.profiles = profiles
        self.user_memories = user_memories


def _empty_conversation():
    return Conversation(conversation_id="c1")


def test_build_chat_request_action_prompt_uses_raw_prompt_and_tools():
    context = _FakeContext(
        assistant_actions=_FakeAssistantActions(keywords=["open "], tools=[{"type": "function"}]),
        device_help=_FakeDeviceHelp(),
    )
    messages, tools = build_chat_request(context, _empty_conversation(), "Open the notes module")
    assert messages[-1] == {"role": "user", "content": "Open the notes module"}
    assert tools == [{"type": "function"}]


def test_build_chat_request_action_prompt_system_message_is_bare_identity_only():
    """No warmth/memory/grounding clauses on the action path — see this module's docstring on why."""
    context = _FakeContext(
        assistant_actions=_FakeAssistantActions(keywords=["open "], tools=[{"type": "function"}]),
        device_help=_FakeDeviceHelp(),
    )
    messages, _ = build_chat_request(context, _empty_conversation(), "Open the notes module")
    assert messages[0] == {"role": "system", "content": build_system_message(context, is_action_request=True)}


def test_build_chat_request_info_prompt_uses_grounding_and_no_tools():
    context = _FakeContext(
        assistant_actions=_FakeAssistantActions(keywords=["open "], tools=[{"type": "function"}]),
        device_help=_FakeDeviceHelp(),
    )
    messages, tools = build_chat_request(context, _empty_conversation(), "What are the symptoms of hypothermia?")
    assert messages[-1] == {"role": "user", "content": "GROUNDED[What are the symptoms of hypothermia?]"}
    assert tools == []


def test_build_chat_request_without_device_help_uses_raw_prompt_for_info_questions():
    context = _FakeContext(assistant_actions=_FakeAssistantActions(keywords=[], tools=[]), device_help=None)
    messages, tools = build_chat_request(context, _empty_conversation(), "What are the symptoms of hypothermia?")
    assert messages[-1] == {"role": "user", "content": "What are the symptoms of hypothermia?"}
    assert tools == []


def test_build_chat_request_without_assistant_actions_never_offers_tools():
    context = _FakeContext(assistant_actions=None, device_help=_FakeDeviceHelp())
    messages, tools = build_chat_request(context, _empty_conversation(), "Open the notes module")
    assert messages[-1] == {"role": "user", "content": "GROUNDED[Open the notes module]"}
    assert tools == []


def test_build_chat_request_includes_bounded_history():
    context = _FakeContext(assistant_actions=_FakeAssistantActions(keywords=[], tools=[]), device_help=_FakeDeviceHelp())
    conversation = Conversation(conversation_id="c1")
    conversation.messages = [
        ConversationMessage(role="user", content="My name is Alex."),
        ConversationMessage(role="assistant", content="Nice to meet you, Alex!"),
    ]
    messages, _ = build_chat_request(context, conversation, "What's my name?")
    assert messages[1] == {"role": "user", "content": "My name is Alex."}
    assert messages[2] == {"role": "assistant", "content": "Nice to meet you, Alex!"}
    assert messages[-1] == {"role": "user", "content": "GROUNDED[What's my name?]"}


def test_build_chat_request_history_never_includes_grounded_augmentation():
    """History entries are the plain displayed text, not a past turn's grounded-with-reference-material version."""
    context = _FakeContext(assistant_actions=_FakeAssistantActions(keywords=[], tools=[]), device_help=_FakeDeviceHelp())
    conversation = Conversation(conversation_id="c1")
    conversation.messages = [ConversationMessage(role="user", content="What are the symptoms of hypothermia?")]
    messages, _ = build_chat_request(context, conversation, "Anything else I should know?")
    assert messages[1] == {"role": "user", "content": "What are the symptoms of hypothermia?"}
    assert "GROUNDED[" not in messages[1]["content"]


# ----------------------------------------------------------------------
# trim_history
# ----------------------------------------------------------------------

def test_trim_history_keeps_everything_under_the_limit():
    messages = [ConversationMessage(role="user", content=str(i)) for i in range(3)]
    assert trim_history(messages, max_messages=12) == messages


def test_trim_history_keeps_only_the_most_recent():
    messages = [ConversationMessage(role="user", content=str(i)) for i in range(20)]
    trimmed = trim_history(messages, max_messages=4)
    assert [m.content for m in trimmed] == ["16", "17", "18", "19"]


def test_trim_history_zero_limit_returns_empty():
    messages = [ConversationMessage(role="user", content="hi")]
    assert trim_history(messages, max_messages=0) == []


# ----------------------------------------------------------------------
# build_user_context_block
# ----------------------------------------------------------------------

class _FakeProfile:
    def __init__(self, name, birthday=None):
        self.name = name
        self.birthday = birthday


class _FakeProfiles:
    def __init__(self, active):
        self._active = active

    def get_active_profile(self):
        return self._active


class _FakeUserMemories:
    def __init__(self, memories):
        self._memories = memories

    def all_memories(self):
        return self._memories


class _FakeMemory:
    def __init__(self, text):
        self.text = text


def test_build_user_context_block_empty_state_invites_learning():
    context = _FakeContext(profiles=None, user_memories=None)
    block = build_user_context_block(context)
    assert "don't know much" in block


def test_build_user_context_block_includes_profile_name():
    context = _FakeContext(profiles=_FakeProfiles(_FakeProfile("Alex")), user_memories=None)
    block = build_user_context_block(context)
    assert "Name: Alex" in block


def test_build_user_context_block_includes_birthday():
    context = _FakeContext(profiles=_FakeProfiles(_FakeProfile("Alex", birthday="1990-03-03")), user_memories=None)
    block = build_user_context_block(context)
    assert "Birthday: March 3" in block


def test_build_user_context_block_includes_memories():
    context = _FakeContext(
        profiles=None,
        user_memories=_FakeUserMemories([_FakeMemory("Loves hiking."), _FakeMemory("Has a dog named Rex.")]),
    )
    block = build_user_context_block(context)
    assert "Loves hiking." in block
    assert "Has a dog named Rex." in block


# ----------------------------------------------------------------------
# format_birthday
# ----------------------------------------------------------------------

def test_format_birthday_strips_year():
    assert format_birthday("1990-03-03") == "March 3"


def test_format_birthday_no_leading_zero_on_day():
    assert format_birthday("2000-07-04") == "July 4"


def test_format_birthday_invalid_input_returned_as_is():
    assert format_birthday("not-a-date") == "not-a-date"


# ----------------------------------------------------------------------
# Memory extraction
# ----------------------------------------------------------------------

def test_build_memory_extraction_prompt_includes_the_user_message():
    """
    Deliberately built from ONLY the user's message, not the
    assistant's reply too — live-model testing found including the
    reply made extraction consistently WORSE (missed obvious facts the
    model caught fine without it). See this function's own docstring
    and core/assistant_chat.py's module docstring for the full finding.
    """
    prompt = build_memory_extraction_prompt("My name is Alex.")
    assert "My name is Alex." in prompt


def test_parse_extracted_memories_none_response():
    assert parse_extracted_memories("NONE") == []


def test_parse_extracted_memories_none_case_insensitive_with_period():
    assert parse_extracted_memories("none.") == []


def test_parse_extracted_memories_single_fact():
    assert parse_extracted_memories("The user's name is Alex.") == [("Other", "The user's name is Alex.")]


def test_parse_extracted_memories_multiple_lines():
    raw = "The user's name is Alex.\nLoves hiking in the Cascades."
    assert parse_extracted_memories(raw) == [("Other", "The user's name is Alex."), ("Other", "Loves hiking in the Cascades.")]


def test_parse_extracted_memories_strips_bullets_and_numbering():
    raw = "- Loves hiking.\n1. Has a dog named Rex.\n2) Works as a nurse."
    assert parse_extracted_memories(raw) == [("Other", "Loves hiking."), ("Other", "Has a dog named Rex."), ("Other", "Works as a nurse.")]


def test_parse_extracted_memories_drops_blank_lines():
    assert parse_extracted_memories("Loves hiking.\n\n\nHas a dog.") == [("Other", "Loves hiking."), ("Other", "Has a dog.")]


def test_parse_extracted_memories_parses_a_real_category_prefix():
    assert parse_extracted_memories("Pets: The user has a dog named Rex.") == [("Pets", "The user has a dog named Rex.")]


def test_parse_extracted_memories_category_prefix_is_case_insensitive():
    assert parse_extracted_memories("pets: The user has a dog named Rex.") == [("Pets", "The user has a dog named Rex.")]


def test_parse_extracted_memories_unrecognized_category_prefix_falls_back_to_other_with_full_line_kept():
    raw = "Sports: The user plays tennis."
    assert parse_extracted_memories(raw) == [("Other", "Sports: The user plays tennis.")]


def test_parse_extracted_memories_mixed_categories_across_lines():
    raw = "Pets: The user has a dog named Rex.\nFitness: The user runs marathons."
    assert parse_extracted_memories(raw) == [
        ("Pets", "The user has a dog named Rex."),
        ("Fitness", "The user runs marathons."),
    ]


def test_parse_extracted_memories_none_input():
    assert parse_extracted_memories(None) == []


def test_parse_extracted_memories_empty_string():
    assert parse_extracted_memories("") == []


# ----------------------------------------------------------------------
# parse_extracted_memories — hedge-phrase safety net
# ----------------------------------------------------------------------
# Live-model testing found the small model doesn't reliably reply with
# the literal "NONE" as instructed — it sometimes paraphrases the same
# "nothing to extract" conclusion as a full sentence instead, which
# would otherwise get stored as if it were a real memory.

def test_parse_extracted_memories_rejects_paraphrased_no_info_sentence():
    raw = "There is no new information provided about the user."
    assert parse_extracted_memories(raw) == []


def test_parse_extracted_memories_rejects_does_not_state_phrasing():
    raw = "The user does not explicitly state a fact about themselves in this message."
    assert parse_extracted_memories(raw) == []


def test_parse_extracted_memories_hedge_phrase_does_not_swallow_other_real_facts():
    raw = "The user has a dog named Rex.\nThere is no new information about anything else."
    assert parse_extracted_memories(raw) == [("Other", "The user has a dog named Rex.")]


# ----------------------------------------------------------------------
# Title generation
# ----------------------------------------------------------------------

def test_build_title_generation_prompt_includes_both_turns():
    prompt = build_title_generation_prompt("Let's plan a hike.", "Sure, where would you like to go?")
    assert "Let's plan a hike." in prompt
    assert "Sure, where would you like to go?" in prompt


def test_clean_generated_title_strips_quotes_and_whitespace():
    assert clean_generated_title('  "Weekend Hiking Plans"  ') == "Weekend Hiking Plans"


def test_clean_generated_title_none_input():
    assert clean_generated_title(None) is None


def test_clean_generated_title_blank_input():
    assert clean_generated_title("   ") is None


def test_clean_generated_title_truncates_overly_long_output():
    long_title = "This is a very long title that goes on and on far past what any real conversation title should ever be"
    cleaned = clean_generated_title(long_title)
    assert len(cleaned) <= 60
    assert not cleaned.endswith((",", ".", ";", ":"))


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
