"""Past conversations on the web: listed newest first with what's in them, one read, one picked back up, one
deleted through its action."""

import pytest

import core.web_conversations as wc
from core.actions import ACTION_TYPES, ActionError
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.conversation_manager import ConversationManager
from core.event_bus import EventBus


@pytest.fixture
def ctx(tmp_path):
    """A context with a conversation store in a temporary folder: one empty, two with messages."""
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.conversations = ConversationManager(context, data_dir=tmp_path)
    context.conversations.create_conversation()  # empty: never listed
    for title, said in (("Truck", "What does the truck need?"), ("Seeds", "When do I start tomatoes?")):
        c = context.conversations.create_conversation()
        context.conversations.set_title(c.conversation_id, title)
        context.conversations.add_message(c.conversation_id, "user", said)
        context.conversations.add_message(c.conversation_id, "assistant", "Here's what I found.")
    return context


def test_the_list_skips_empty_ones_and_shows_the_first_question(ctx):
    page = wc.history(ctx, current_id="")
    assert page["total"] == 2 and {c["title"] for c in page["conversations"]} == {"Truck", "Seeds"}
    seeds = next(c for c in page["conversations"] if c["title"] == "Seeds")
    assert seeds["count"] == 2 and seeds["first"] == "When do I start tomatoes?"
    assert wc.one(ctx, seeds["id"])["messages"][1] == {"role": "assistant", "content": "Here's what I found."}
    assert wc.one(ctx, "nope") is None


def test_picking_one_up_marks_it_used_now_and_delete_runs_through_its_action(ctx):
    truck = next(c for c in ctx.conversations.all_conversations() if c.title == "Truck")
    truck.updated_at = "2020-01-01T00:00:00"
    wc.pick_up(ctx, truck.conversation_id)
    assert truck.updated_at > "2026"
    with pytest.raises(ValueError):
        wc.pick_up(ctx, "nope")
    ACTION_TYPES["conversation.delete"].describe(ctx, {"conversation_id": truck.conversation_id})
    ACTION_TYPES["conversation.delete"].execute(ctx, {"conversation_id": truck.conversation_id})
    assert wc.history(ctx)["total"] == 1
    with pytest.raises(ActionError):
        ACTION_TYPES["conversation.delete"].describe(ctx, {"conversation_id": truck.conversation_id})
