"""
tests.test_intent_manager
============================

Unit tests for core.intent_manager. Isolates _DATA_DIR/_INTENTS_FILE
into a tmp_path scratch area, same monkeypatch pattern as
test_project_manager.py's isolated_paths.
"""

from __future__ import annotations

import pytest

import core.intent_manager as intent_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.intent_manager import IntentManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    intents_file = data_dir / "intents.json"
    monkeypatch.setattr(intent_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(intent_manager_module, "_INTENTS_FILE", intents_file)
    return data_dir, intents_file


def _make_manager() -> IntentManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return IntentManager(context)


def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.all_intents() == []


def test_add_intent_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    manager.add_intent(name="Homestead Independence", description="Solar, food, water.")

    reloaded = IntentManager(manager.context)
    intents = reloaded.all_intents()
    assert len(intents) == 1
    assert intents[0].name == "Homestead Independence"
    assert intents[0].description == "Solar, food, water."


def test_add_intent_defaults(isolated_paths):
    manager = _make_manager()
    intent = manager.add_intent(name="X")
    assert intent.status == "Active"
    assert intent.primary is False


def test_update_intent_changes_fields(isolated_paths):
    manager = _make_manager()
    intent = manager.add_intent(name="X")
    manager.update_intent(intent.intent_id, name="Y", status="Paused")
    updated = manager.get_intent(intent.intent_id)
    assert updated.name == "Y"
    assert updated.status == "Paused"


def test_update_intent_rejects_primary_field(isolated_paths):
    manager = _make_manager()
    intent = manager.add_intent(name="X")
    with pytest.raises(ValueError):
        manager.update_intent(intent.intent_id, primary=True)


def test_update_intent_rejects_created_at(isolated_paths):
    manager = _make_manager()
    intent = manager.add_intent(name="X")
    with pytest.raises(ValueError):
        manager.update_intent(intent.intent_id, created_at="2020-01-01T00:00:00")


def test_update_intent_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.update_intent("does-not-exist", name="Y")


def test_delete_intent_removes_it(isolated_paths):
    manager = _make_manager()
    intent = manager.add_intent(name="X")
    manager.delete_intent(intent.intent_id)
    assert manager.get_intent(intent.intent_id) is None


def test_get_intent_returns_none_for_unknown_id(isolated_paths):
    manager = _make_manager()
    assert manager.get_intent("does-not-exist") is None


# ------------------------------------------------------------------
# primary / set_primary
# ------------------------------------------------------------------

def test_set_primary_marks_exactly_one(isolated_paths):
    manager = _make_manager()
    a = manager.add_intent(name="A")
    b = manager.add_intent(name="B")

    manager.set_primary(a.intent_id)
    assert manager.get_intent(a.intent_id).primary is True
    assert manager.get_intent(b.intent_id).primary is False

    manager.set_primary(b.intent_id)
    assert manager.get_intent(a.intent_id).primary is False
    assert manager.get_intent(b.intent_id).primary is True


def test_set_primary_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.set_primary("does-not-exist")


def test_primary_intent_returns_none_when_none_set(isolated_paths):
    manager = _make_manager()
    manager.add_intent(name="A")
    assert manager.primary_intent() is None


def test_primary_intent_returns_the_primary_one(isolated_paths):
    manager = _make_manager()
    manager.add_intent(name="A")
    b = manager.add_intent(name="B")
    manager.set_primary(b.intent_id)
    assert manager.primary_intent().intent_id == b.intent_id


def test_add_intent_with_primary_true_sets_it_immediately(isolated_paths):
    manager = _make_manager()
    intent = manager.add_intent(name="A", primary=True)
    assert manager.get_intent(intent.intent_id).primary is True


def test_add_intent_with_primary_true_unsets_previous_primary(isolated_paths):
    manager = _make_manager()
    a = manager.add_intent(name="A", primary=True)
    b = manager.add_intent(name="B", primary=True)
    assert manager.get_intent(a.intent_id).primary is False
    assert manager.get_intent(b.intent_id).primary is True
