"""
Slice A, "Talk it out" (core/talk_it_out.py) end to end through
core/assistant_turn.run_assistant_turn with a fake model: modes,
privacy of what's written to disk, the safety floor, journaling, and
the journal tools. Asserts facts and structure, never generated wording.
"""

import json

import pytest

import core.config_manager as config_module
import core.conversation_manager as conversation_module
import core.private_journal as pj
import core.user_memory_manager as memory_module
from core.app_context import AppContext
from core.assistant_chat import build_chat_request
from core.assistant_turn import run_assistant_turn, run_followup
from core.config_manager import ConfigManager
from core.conversation_manager import ConversationManager
from core.conversation_modes import DIRECT, LISTEN, MODE_INSTRUCTIONS
from core.event_bus import EventBus
from core.llm_manager import ChatReply, ToolCall
from core.private_journal import PrivateJournalManager
from core.talk_it_out import (
    NOT_SET_UP_NOTICE, journal_context_block, parse_journal_organization,
)
from core.user_memory_manager import UserMemoryManager
from tests.assistant_registry import build_desktop_registry

PASS = "correct horse battery"
ORGANIZED = "Title: Long shift blues\nMood: drained\nThemes: work, greenhouse\nSummary: You talked about a long shift."


class FakeLLM:
    def __init__(self):
        self.reply = ChatReply(content="That sounds exhausting.")
        self.generated = ORGANIZED
        self.chat_calls = []
        self.generate_calls = []

    def chat_with_tools(self, messages, tools):
        self.chat_calls.append((messages, tools))
        return self.reply

    def generate(self, prompt):
        self.generate_calls.append(prompt)
        return self.generated


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(conversation_module, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(conversation_module, "_CONVERSATIONS_FILE", tmp_path / "conversations.json")
    monkeypatch.setattr(memory_module, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(memory_module, "_USER_MEMORIES_FILE", tmp_path / "user_memories.json")
    monkeypatch.setattr(pj, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(pj, "_KEYS_FILE", tmp_path / "private_journal_keys.json")
    monkeypatch.setattr(pj, "_ENTRIES_FILE", tmp_path / "private_journal.json")
    monkeypatch.setattr(pj, "_RSA_KEY_SIZE", 2048)
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.conversations = ConversationManager(context)
    context.user_memories = UserMemoryManager(context)
    context.private_journal = PrivateJournalManager(context)
    context.assistant_actions = build_desktop_registry()
    context.llm = FakeLLM()
    context.tmp = tmp_path
    return context


def turn(ctx, text):
    conversation = ctx.conversations.get_or_create_active_conversation()
    result = run_assistant_turn(ctx, conversation, text)
    run_followup(ctx, conversation, result.followup)
    # run_assistant_turn is the voice/phone path, which doesn't save by
    # itself; saving here checks what *would* reach conversations.json.
    ctx.conversations.save()
    return conversation, result


def saved_conversation_text(ctx) -> str:
    return (ctx.tmp / "conversations.json").read_text()


# ------------------------------------------------------------------ modes


def test_mode_sticks_and_shapes_the_system_prompt(ctx):
    conversation, _ = turn(ctx, "MIA, no bullshit. Am I wasting my time at this job?")
    assert conversation.mode == DIRECT
    messages, tools = ctx.llm.chat_calls[-1]
    assert MODE_INSTRUCTIONS[DIRECT] in messages[0]["content"] and tools == []
    turn(ctx, "What else?")
    assert MODE_INSTRUCTIONS[DIRECT] in ctx.llm.chat_calls[-1][0][0]["content"]
    turn(ctx, "ok, back to normal")
    assert conversation.mode == "companion"


def test_vent_mentioning_records_gets_no_tools_but_a_command_does(ctx):
    conversation, _ = turn(ctx, "I need to vent")
    turn(ctx, "The truck broke down again and I had to pay for groceries on the card")
    assert ctx.llm.chat_calls[-1][1] == []
    turn(ctx, "Add milk to the grocery list")
    assert "add_grocery_item" in [t["function"]["name"] for t in ctx.llm.chat_calls[-1][1]]


def test_personal_path_has_no_help_doc_grounding(ctx):
    conversation = ctx.conversations.get_or_create_active_conversation()
    conversation.mode = LISTEN
    messages, _ = build_chat_request(ctx, conversation, "I'm tired of doing the same thing every day")
    assert "ONLY the reference material" not in messages[0]["content"]
    assert messages[-1]["content"] == "I'm tired of doing the same thing every day"


# ------------------------------------------------------------------ safety floor


def test_safety_floor_answers_without_the_model(ctx):
    ctx.config.set("assistant.safety.trusted_contact", "my brother Josh")
    conversation, result = turn(ctx, "honestly I want to kill myself")
    assert ctx.llm.chat_calls == [] and ctx.llm.generate_calls == []
    assert "988" in result.replies[0] and "Josh" in result.replies[0]
    assert conversation.mode == LISTEN
    assert ctx.user_memories.all_memories() == []


def test_safety_floor_works_with_the_model_down(ctx):
    ctx.llm = None
    _, result = turn(ctx, "I don't want to live anymore")
    assert "988" in result.replies[0]


# ------------------------------------------------------------------ privacy on disk


def test_normal_conversation_extracts_memories_and_persists(ctx):
    ctx.llm.generated = "Values: The user values time with family."
    turn(ctx, "Family time matters more to me than anything")
    assert [m.category for m in ctx.user_memories.all_memories()] == ["Values"]
    assert "Family time matters" in saved_conversation_text(ctx)


def test_off_the_record_saves_nothing(ctx):
    conversation, result = turn(ctx, "Off the record: I've been thinking about quitting")
    turn(ctx, "My boss has been impossible lately")
    assert result.followup is None and ctx.llm.generate_calls == []
    text = saved_conversation_text(ctx)
    assert "quitting" not in text and "impossible" not in text and "exhausting" not in text
    assert json.loads(text)[0]["title"] == "Off the record"
    assert ctx.user_memories.all_memories() == []
    turn(ctx, "ok back on the record. I like my coffee black")
    assert "coffee black" in saved_conversation_text(ctx)


def test_journal_without_setup_says_so_and_saves_nothing(ctx):
    conversation, result = turn(ctx, "I want to journal")
    assert result.replies[0] == NOT_SET_UP_NOTICE
    assert ctx.private_journal.entry_count() == 0
    assert json.loads(saved_conversation_text(ctx))[0]["messages"] == []


# ------------------------------------------------------------------ journaling


def test_journal_session_is_saved_encrypted_and_organized(ctx):
    ctx.private_journal.setup(PASS)
    ctx.private_journal.lock()  # MIA can still write
    conversation, _ = turn(ctx, "I want to journal")
    assert conversation.journal and conversation.mode == LISTEN
    turn(ctx, "Work dragged today. I kept thinking about the greenhouse.")
    assert ctx.private_journal.entry_count() == 1  # one entry per session, replaced each turn
    assert ctx.user_memories.all_memories() == []  # journaled text never becomes a plain memory
    text = saved_conversation_text(ctx)
    assert "greenhouse" not in text and "exhausting" not in text
    assert json.loads(text)[0]["title"] == "Journal session"

    ctx.private_journal.unlock(PASS)
    [entry] = ctx.private_journal.all_entries()
    assert entry.title == "Long shift blues" and entry.mood == "drained" and entry.themes == ["work", "greenhouse"]
    assert "greenhouse" in entry.user_text and any(e.role == "assistant" for e in entry.exchanges)


def test_journal_context_used_only_when_unlocked(ctx):
    ctx.private_journal.setup(PASS)
    turn(ctx, "I want to journal")
    turn(ctx, "Rough week at work")
    assert "Long shift blues" in journal_context_block(ctx)
    ctx.private_journal.lock()
    assert journal_context_block(ctx) == ""


def test_done_journaling_starts_a_new_entry_next_time(ctx):
    ctx.private_journal.setup(PASS)
    turn(ctx, "I want to journal")
    turn(ctx, "first session")
    turn(ctx, "I'm done journaling")
    turn(ctx, "let's journal")
    turn(ctx, "second session")
    assert ctx.private_journal.entry_count() == 2


# ------------------------------------------------------------------ reading the journal back


def test_journal_tools_and_private_turns(ctx):
    ctx.private_journal.setup(PASS)
    turn(ctx, "I want to journal")
    turn(ctx, "The Chase card is finally paid off")
    turn(ctx, "back to normal")

    ctx.llm.reply = ChatReply(content="", tool_calls=[ToolCall(name="read_private_journal", arguments={"query": "chase"})])
    conversation, result = turn(ctx, "What did I say in my journal about the Chase card?")
    assert "read_private_journal" in [t["function"]["name"] for t in ctx.llm.chat_calls[-1][1]]
    assert "Long shift blues" in result.replies[0]
    assert "Chase" not in saved_conversation_text(ctx)  # the question and the answer stay out of history

    ctx.private_journal.lock()
    _, result = turn(ctx, "What's in my journal?")
    assert "locked" in result.replies[0]


def test_themes_tool(ctx):
    ctx.private_journal.setup(PASS)
    turn(ctx, "I want to journal")
    turn(ctx, "work again")
    reply = ctx.assistant_actions.execute(ctx, "get_journal_themes", {})
    assert reply.startswith("In the last 30 days you journaled 1 time.") and "work (1)" in reply and "drained" in reply


# ------------------------------------------------------------------ parsing


@pytest.mark.parametrize("raw, title, themes", [
    (ORGANIZED, "Long shift blues", ["work", "greenhouse"]),
    ("**Title:** \"Money wins\"\n- Mood: proud\n* Themes: Debt, Family.\nSummary: You talked about debt.", "Money wins", ["debt", "family"]),
])
def test_parse_organization(raw, title, themes):
    organized = parse_journal_organization(raw)
    assert organized["title"] == title and organized["themes"] == themes


@pytest.mark.parametrize("raw", [None, "", "I'm not sure what to say.", "Mood: fine"])
def test_parse_organization_rejects_junk(raw):
    assert parse_journal_organization(raw) is None
