"""
tests.test_turn_harness
=========================

Turns through the real engine with a scripted model (roadmap 2.8, 2026-11-10):
the server built on the real headless context (build_core_context), the real
model manager with a backend that replies from a script, and the real tools.
Each test says what was asked, what the model "chose", and checks what changed
in the stores, not just what was said, and that "undo that" puts it back.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import server.app as server_app_module
from core.llm_manager import ChatReply, LLMManager, ToolCall
from core.personal_data import view_for
from tests.test_server_app import _profile_id, context  # noqa: F401  (the fixture: the real headless context)


def _notes(context) -> list[str]:
    """The titles in the signed-in person's own journal (a phone turn runs on their view)."""
    return [e.title for e in view_for(context, _profile_id(context)).journal.all_entries()]


class _Script:
    """A model backend that answers each chat from a script, in order, and remembers which tools it was offered."""

    def __init__(self, *replies):
        """The replies to give in turn."""
        self._model, self.replies, self.offered = "scripted", list(replies), []

    def chat(self, messages, tools, timeout):
        """The next scripted reply (plain words once the script runs out)."""
        self.offered.append([t.get("function", {}).get("name", "") for t in tools])
        return self.replies.pop(0) if self.replies else ChatReply(content="All done.")

    def generate(self, prompt, timeout):
        """No memories pulled out of these turns."""
        return ""

    def is_available(self, timeout):
        """Always up."""
        return True


@pytest.fixture
def talk(context):  # noqa: F811
    """A signed-in client and a way to script the model: talk(script) -> post(text) -> the turn's reply."""
    context.llm = LLMManager(context)
    client = TestClient(server_app_module.create_app(context))
    token = client.post("/api/login", json={"profile_id": "Alice", "password": "hunter2"}).json()["token"]
    auth = {"Authorization": f"Bearer {token}"}

    def run(script: _Script):
        """Uses this script for the model; returns a function that says something and gives back the reply."""
        context.llm.use_backend(script)
        return lambda text: client.post("/api/voice/text", json={"text": text}, headers=auth).json()

    return run


def test_a_note_the_model_adds_is_in_the_store_and_undo_takes_it_back(talk, context):  # noqa: F811
    script = _Script(ChatReply(content="", tool_calls=[ToolCall(name="add_note", arguments={
        "title": "Coop door", "body": "The latch sticks in the cold."})]))
    say = talk(script)
    reply = say("jot down that the coop door latch sticks when it's cold")
    assert "Coop door" in " ".join(reply["replies"])
    assert "add_note" in script.offered[0]
    assert _notes(context).count("Coop door") == 1
    say("undo that")
    assert "Coop door" not in _notes(context)


def test_a_tool_the_model_wasn_t_offered_changes_nothing(talk, context):  # noqa: F811
    script = _Script(ChatReply(content="", tool_calls=[ToolCall(name="delete_note", arguments={"title": "Coop door"})]))
    view_for(context, _profile_id(context)).journal.add_entry(title="Coop door", body="kept")
    reply = talk(script)("what's the weather like for the garden this week?")
    assert "delete_note" not in script.offered[0]
    assert "Coop door" in _notes(context)
    assert reply["replies"]
