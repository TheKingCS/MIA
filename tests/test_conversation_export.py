"""A conversation taken out of the chat (core/conversation_export.py): the export in Markdown and JSON, the summary
of the whole of it with and without a model, how it's asked for in words, and the action that saves it to Files."""

import json
from datetime import datetime
from types import SimpleNamespace

import pytest

import core.conversation_export as ce
from core.actions import ACTION_TYPES, ActionError
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.conversation_manager import ConversationManager, ConversationMessage
from core.event_bus import EventBus
from core.my_files import FOLDER as FILES


def _talk(*said, title="Coop plans"):
    """A conversation of (role, content) pairs a minute apart, in memory."""
    messages = [ConversationMessage(role=role, content=content, timestamp=f"2026-11-08T09:{i:02d}:00")
                for i, (role, content) in enumerate(said)]
    return SimpleNamespace(conversation_id="c1", title=title, created_at="2026-11-08T09:00:00",
                           updated_at="2026-11-08T09:30:00", messages=messages)


class _Model:
    """A model that keeps each prompt it was sent and answers from a list (the last answer repeats)."""

    def __init__(self, *answers):
        """Nothing asked yet."""
        self.answers, self.asked = list(answers), []

    def generate(self, prompt, timeout=None):
        """Keeps the prompt; gives the next answer."""
        self.asked.append(prompt)
        return self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]


@pytest.fixture
def ctx(tmp_path):
    """A context with a conversation store and a Files folder, both in a temporary folder; one conversation kept."""
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.journal = SimpleNamespace(data_dir=tmp_path)
    context.conversations = ConversationManager(context, data_dir=tmp_path)
    c = context.conversations.create_conversation()
    context.conversations.set_title(c.conversation_id, "Coop: plans / costs?")
    context.conversations.add_message(c.conversation_id, "user", "How big should the coop be?")
    context.conversations.add_message(c.conversation_id, "assistant", "Four square feet a bird inside.")
    context.kept_id = c.conversation_id
    return context


def test_only_what_was_kept_is_ever_taken_out():
    talk = _talk(("user", "Just between us."), ("system", "a note"), ("assistant", ""), ("user", "And the coop?"))
    talk.messages[0].privacy = "private"
    assert [m.content for m in ce.kept(talk)] == ["And the coop?"]


def test_the_markdown_export_has_every_message_in_order_with_who_said_it_and_when():
    out = ce.export_of(_talk(("user", "How big?"), ("assistant", "Four square feet a bird.\n\n- inside\n- more outside")),
                       now=datetime(2026, 11, 9, 8, 5))
    assert out["filename"] == "Coop plans 2026-11-09.md" and out["count"] == 2 and out["mime"] == "text/markdown"
    text = out["text"]
    assert text.startswith("# Coop plans\n\nExported 2026-11-09 08:05 · 2 messages")
    assert text.index("**You** · 2026-11-08 09:00") < text.index("How big?") < text.index("**MIA** · 2026-11-08 09:01")
    assert "- inside\n- more outside" in text


def test_the_json_export_keeps_roles_times_and_the_words_exactly():
    out = ce.export_of(_talk(("user", "Café at 9?"), ("assistant", "Yes: 9.")), "json", now=datetime(2026, 11, 9, 8, 5))
    data = json.loads(out["text"])
    assert out["filename"].endswith(".json") and data["title"] == "Coop plans" and data["exported"].startswith("2026-11-09")
    assert data["messages"] == [{"role": "user", "content": "Café at 9?", "at": "2026-11-08T09:00:00"},
                                {"role": "assistant", "content": "Yes: 9.", "at": "2026-11-08T09:01:00"}]
    with pytest.raises(ValueError):
        ce.export_of(_talk(("user", "x")), "pdf")


def test_a_time_kept_in_utc_is_shown_in_local_time_and_a_bad_one_is_left_out():
    local = datetime.fromisoformat("2026-11-08T17:30:00+00:00").astimezone().strftime("%Y-%m-%d %H:%M")
    assert ce._when("2026-11-08T17:30:00+00:00") == local
    assert ce._when("2026-11-08T09:04:59") == "2026-11-08 09:04" and ce._when("soon") == "" and ce._when("") == ""


def test_a_long_conversation_is_read_in_parts_that_together_hold_every_line():
    lines = [f"Person: question {i} " + "x" * 300 for i in range(120)]
    parts = ce._parts(lines)
    assert 1 < len(parts) <= ce.MOST_PARTS + 1
    assert "\n".join(parts).split("\n") == lines
    assert ce._parts(lines[:3]) == ["\n".join(lines[:3])]


def test_a_summary_of_a_short_conversation_is_one_reading_under_a_counted_first_line():
    model = _Model("**Topics**\n- The coop\nDecided\n- Nothing\nStill open\n- Its size\nTo do\n- Nothing")
    out = ce.summary_of(SimpleNamespace(llm=model), _talk(("user", "How big should the coop be?"), ("assistant", "Depends.")))
    assert out["by"] == "model" and out["count"] == 2
    assert out["text"].startswith("2 messages, 2026-11-08 09:00 to 09:01.\n\nTopics\n- The coop")
    assert len(model.asked) == 1 and "Person: How big should the coop be?" in model.asked[0] and "MIA: Depends." in model.asked[0]


def test_a_summary_of_a_long_conversation_reads_every_part_before_it_is_written():
    said = [("user" if i % 2 == 0 else "assistant", f"point {i} " + "y" * 400) for i in range(60)]
    model = _Model("Topics\n- part", "Topics\n- part", "Topics\n- part", "Topics\n- part", "Topics\n- part", "Topics\n- part",
                   "Topics\n- part")
    out = ce.summary_of(SimpleNamespace(llm=model), _talk(*said))
    assert out["by"] == "model" and len(model.asked) >= 3
    read = "\n".join(model.asked[:-1])
    assert all(f"point {i} " in read for i in range(60))
    assert "notes on each part" in model.asked[-1]


def test_with_no_model_the_summary_says_so_and_lists_what_was_asked_in_order():
    talk = _talk(("user", "How big should the coop be?"), ("assistant", "Depends."), ("user", "And the run?"))
    for context in (SimpleNamespace(), SimpleNamespace(llm=_Model(""))):
        out = ce.summary_of(context, talk)
        assert out["by"] == "code" and "language model isn't running" in out["text"]
        assert out["text"].index("- How big should the coop be?") < out["text"].index("- And the run?")
    assert ce.summary_of(SimpleNamespace(), _talk())["text"] == ce.NOTHING_SAID


def test_asking_for_this_conversation_is_told_from_one_with_somebody_else_and_from_a_no():
    for said in ("Summarize this conversation", "can you give me a summary of our chat?", "Recap what we've talked about",
                 "sum up this discussion please", "conversation summary"):
        assert ce.wants(said) == ("summary",), said
    assert ce.wants("Export this conversation") == ("export", "markdown")
    assert ce.wants("export this chat as JSON") == ("export", "json")
    assert ce.wants("save this conversation to my files") == ("export", "markdown")
    for said in ("Summarize the conversation I had with the contractor", "Don't save this conversation",
                 "What's a good conversation starter?", "Summarize my week", "", "export my budget"):
        assert ce.wants(said) is None, said


def test_asked_for_in_talk_the_request_itself_is_left_out_and_the_export_lands_in_files(ctx):
    talk = ctx.conversations.get_conversation(ctx.kept_id)
    assert ce.reply(ctx, _talk(("user", "Summarize this conversation")), "Summarize this conversation") is None
    ctx.conversations.add_message(ctx.kept_id, "user", "Summarize this conversation")
    said, opens = ce.reply(ctx, talk, "Summarize this conversation")
    assert said.startswith("2 messages") and opens == ""
    said, opens = ce.reply(ctx, talk, "export this chat as JSON")
    assert said.startswith("Saved to Files: Conversations/") and opens == "files.html#Conversations"
    saved = json.loads((ctx.journal.data_dir / FILES / said.split(": ", 1)[1]).read_text(encoding="utf-8"))
    assert [m["content"] for m in saved["messages"]] == ["How big should the coop be?", "Four square feet a bird inside."]


def test_the_action_saves_a_kept_conversation_to_files_under_a_name_a_folder_can_hold(ctx):
    export, asked = ACTION_TYPES["conversation.export"], {"conversation_id": ctx.kept_id, "form": "markdown"}
    assert export.describe(ctx, asked).startswith("Save “Coop: plans / costs?” to Files as Markdown")
    done = export.execute(ctx, asked)
    assert done.startswith("Saved to Files: Conversations/Coop")
    path = ctx.journal.data_dir / FILES / done.split(": ", 1)[1]
    assert path.suffix == ".md" and "**MIA**" in path.read_text(encoding="utf-8")
    assert export.execute(ctx, {"conversation_id": ctx.kept_id}) != done  # a second export never writes over the first
    with pytest.raises(ActionError):
        export.describe(ctx, {"conversation_id": "nope"})


def test_headings_the_model_wrote_as_bullets_or_with_colons_stand_as_headings():
    said = ce._tidy("- Topics\n- The coop\n\n- **Decided:**\n- Nothing\nStill open\n- Its size\n* To do\n- Nothing\n")
    assert said == "Topics\n- The coop\n\nDecided\n- Nothing\n\nStill open\n- Its size\n\nTo do\n- Nothing"
    assert ce._tidy("- Topics we covered\n- Nothing decided") == "- Topics we covered\n- Nothing decided"
