"""
tests.test_conversation_manager
==================================

Unit tests for core.conversation_manager. Isolates _DATA_DIR/
_CONVERSATIONS_FILE into a tmp_path scratch area, same monkeypatch
pattern as test_mission_manager.py's isolated_paths. Also isolates
config_manager's _CONFIG_FILE, since set_active_conversation_id() calls
context.config.save() — the exact real test-pollution gap 5.14 found
and fixed elsewhere in this project (see docs/ROADMAP.md), not
repeating it here.
"""

from __future__ import annotations

import pytest

import core.config_manager as config_manager_module
import core.conversation_manager as conversation_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.conversation_manager import DEFAULT_TITLE, ConversationManager
from core.event_bus import EventBus


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(conversation_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(conversation_manager_module, "_CONVERSATIONS_FILE", data_dir / "conversations.json")
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")


def _make_manager() -> ConversationManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return ConversationManager(context)


# ----------------------------------------------------------------------
# CRUD
# ----------------------------------------------------------------------

def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.all_conversations() == []


def test_create_conversation_has_default_title(isolated_paths):
    manager = _make_manager()
    conversation = manager.create_conversation()
    assert conversation.title == DEFAULT_TITLE
    assert conversation.messages == []


def test_create_conversation_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    created = manager.create_conversation()

    reloaded = _make_manager()
    assert reloaded.get_conversation(created.conversation_id) is not None


def test_add_message_appends_and_bumps_updated_at(isolated_paths):
    manager = _make_manager()
    conversation = manager.create_conversation()
    original_updated_at = conversation.updated_at

    updated = manager.add_message(conversation.conversation_id, "user", "Hello")
    assert len(updated.messages) == 1
    assert updated.messages[0].role == "user"
    assert updated.messages[0].content == "Hello"
    assert updated.updated_at >= original_updated_at


def test_add_message_unknown_conversation_returns_none(isolated_paths):
    manager = _make_manager()
    assert manager.add_message("does-not-exist", "user", "Hello") is None


def test_set_title(isolated_paths):
    manager = _make_manager()
    conversation = manager.create_conversation()
    updated = manager.set_title(conversation.conversation_id, "Hiking Plans")
    assert updated.title == "Hiking Plans"
    assert manager.get_conversation(conversation.conversation_id).title == "Hiking Plans"


def test_delete_conversation(isolated_paths):
    manager = _make_manager()
    conversation = manager.create_conversation()
    manager.delete_conversation(conversation.conversation_id)
    assert manager.get_conversation(conversation.conversation_id) is None


def test_delete_is_idempotent(isolated_paths):
    manager = _make_manager()
    manager.delete_conversation("does-not-exist")  # must not raise


def test_all_conversations_sorted_most_recently_updated_first(isolated_paths):
    manager = _make_manager()
    first = manager.create_conversation()
    second = manager.create_conversation()
    manager.add_message(first.conversation_id, "user", "touch this one last")

    ordered = manager.all_conversations()
    assert ordered[0].conversation_id == first.conversation_id
    assert ordered[1].conversation_id == second.conversation_id


def test_load_handles_corrupt_json_gracefully(isolated_paths, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "conversations.json").write_text("{not valid json", encoding="utf-8")
    manager = _make_manager()
    assert manager.all_conversations() == []


# ----------------------------------------------------------------------
# Active conversation
# ----------------------------------------------------------------------

def test_get_active_conversation_id_defaults_to_none(isolated_paths):
    manager = _make_manager()
    assert manager.get_active_conversation_id() is None


def test_get_or_create_active_conversation_creates_one_the_first_time(isolated_paths):
    manager = _make_manager()
    conversation = manager.get_or_create_active_conversation()
    assert manager.get_active_conversation_id() == conversation.conversation_id


def test_get_or_create_active_conversation_reuses_the_existing_active_one(isolated_paths):
    manager = _make_manager()
    first_call = manager.get_or_create_active_conversation()
    second_call = manager.get_or_create_active_conversation()
    assert first_call.conversation_id == second_call.conversation_id


def test_get_or_create_active_conversation_recreates_if_active_was_deleted(isolated_paths):
    manager = _make_manager()
    original = manager.get_or_create_active_conversation()
    manager.delete_conversation(original.conversation_id)

    replacement = manager.get_or_create_active_conversation()
    assert replacement.conversation_id != original.conversation_id


def test_start_new_active_conversation_always_creates_a_fresh_one(isolated_paths):
    manager = _make_manager()
    first = manager.get_or_create_active_conversation()
    second = manager.start_new_active_conversation()

    assert second.conversation_id != first.conversation_id
    assert manager.get_active_conversation_id() == second.conversation_id


def test_deleting_the_active_conversation_clears_the_active_pointer(isolated_paths):
    manager = _make_manager()
    conversation = manager.get_or_create_active_conversation()
    manager.delete_conversation(conversation.conversation_id)
    assert manager.get_active_conversation_id() is None


# ----------------------------------------------------------------------
# conversation.updated event
# ----------------------------------------------------------------------

def test_add_message_publishes_conversation_updated_event(isolated_paths):
    context = AppContext(config=ConfigManager(), events=EventBus())
    manager = ConversationManager(context)
    conversation = manager.create_conversation()

    received = []
    context.events.subscribe("conversation.updated", lambda **kwargs: received.append(kwargs))

    manager.add_message(conversation.conversation_id, "user", "Hello")
    assert received == [{"conversation_id": conversation.conversation_id}]


def test_set_title_publishes_conversation_updated_event(isolated_paths):
    context = AppContext(config=ConfigManager(), events=EventBus())
    manager = ConversationManager(context)
    conversation = manager.create_conversation()

    received = []
    context.events.subscribe("conversation.updated", lambda **kwargs: received.append(kwargs))

    manager.set_title(conversation.conversation_id, "New Title")
    assert received == [{"conversation_id": conversation.conversation_id}]
