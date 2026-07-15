"""
tests.test_user_memory_manager
=================================

Unit tests for core.user_memory_manager. is_duplicate_memory() is
tested directly (pure, deterministic). UserMemoryManager is tested
against a tmp_path scratch area, same monkeypatch pattern as
test_mission_manager.py's isolated_paths.
"""

from __future__ import annotations

import pytest

import core.user_memory_manager as user_memory_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.user_memory_manager import UserMemoryManager, is_duplicate_memory


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(user_memory_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(user_memory_manager_module, "_USER_MEMORIES_FILE", data_dir / "user_memories.json")


def _make_manager() -> UserMemoryManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return UserMemoryManager(context)


# ----------------------------------------------------------------------
# is_duplicate_memory (pure)
# ----------------------------------------------------------------------

def test_is_duplicate_memory_exact_match():
    assert is_duplicate_memory("Loves hiking", ["Loves hiking"]) is True


def test_is_duplicate_memory_case_and_whitespace_insensitive():
    assert is_duplicate_memory("  loves HIKING  ", ["Loves hiking"]) is True


def test_is_duplicate_memory_not_a_match():
    assert is_duplicate_memory("Loves kayaking", ["Loves hiking"]) is False


def test_is_duplicate_memory_empty_existing_list():
    assert is_duplicate_memory("Loves hiking", []) is False


# ----------------------------------------------------------------------
# UserMemoryManager CRUD
# ----------------------------------------------------------------------

def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.all_memories() == []


def test_add_memory(isolated_paths):
    manager = _make_manager()
    memory = manager.add_memory("The user's name is Alex.")
    assert memory is not None
    assert memory.text == "The user's name is Alex."
    assert manager.all_memories() == [memory]


def test_add_memory_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    manager.add_memory("Loves hiking in the Cascades.")

    reloaded = _make_manager()
    assert len(reloaded.all_memories()) == 1
    assert reloaded.all_memories()[0].text == "Loves hiking in the Cascades."


def test_add_memory_rejects_duplicate(isolated_paths):
    manager = _make_manager()
    manager.add_memory("Loves hiking.")
    duplicate = manager.add_memory("loves hiking.")
    assert duplicate is None
    assert len(manager.all_memories()) == 1


def test_add_memory_rejects_blank_text(isolated_paths):
    manager = _make_manager()
    assert manager.add_memory("   ") is None
    assert manager.all_memories() == []


def test_add_memory_records_source_conversation(isolated_paths):
    manager = _make_manager()
    memory = manager.add_memory("Has a dog named Rex.", source_conversation_id="conv123")
    assert memory.source_conversation_id == "conv123"


def test_delete_memory(isolated_paths):
    manager = _make_manager()
    memory = manager.add_memory("Loves hiking.")
    manager.delete_memory(memory.memory_id)
    assert manager.all_memories() == []


def test_delete_memory_is_idempotent(isolated_paths):
    manager = _make_manager()
    manager.delete_memory("does-not-exist")  # must not raise


def test_clear_all(isolated_paths):
    manager = _make_manager()
    manager.add_memory("Fact one.")
    manager.add_memory("Fact two.")
    manager.clear_all()
    assert manager.all_memories() == []


def test_all_memories_sorted_newest_first(isolated_paths):
    # created_at has only second-level precision (timespec="seconds"),
    # so two real add_memory() calls in the same test could collide on
    # the same wall-clock second — set distinguishable timestamps
    # directly rather than relying on real-time granularity.
    manager = _make_manager()
    first = manager.add_memory("Fact one.")
    second = manager.add_memory("Fact two.")
    first.created_at = "2026-07-14T10:00:00"
    second.created_at = "2026-07-14T11:00:00"

    ordered = manager.all_memories()
    assert ordered[0].memory_id == second.memory_id
    assert ordered[1].memory_id == first.memory_id


def test_load_handles_corrupt_json_gracefully(isolated_paths, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "user_memories.json").write_text("{not valid json", encoding="utf-8")
    manager = _make_manager()
    assert manager.all_memories() == []
