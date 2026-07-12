"""
tests.test_activity_log_manager
==================================

Unit tests for core.activity_log_manager. Isolates _DATA_DIR/
_ACTIVITY_LOG_FILE into a tmp_path scratch area (same monkeypatch
pattern as test_inventory_manager.py's isolated_paths).
"""

from __future__ import annotations

import pytest

import core.activity_log_manager as activity_log_manager_module
from core.activity_log_manager import ActivityLogManager
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    log_file = data_dir / "activity_log.json"
    monkeypatch.setattr(activity_log_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(activity_log_manager_module, "_ACTIVITY_LOG_FILE", log_file)
    return data_dir, log_file


class _FakeNotification:
    def __init__(self, title, message) -> None:
        self.title = title
        self.message = message


def _make_manager() -> tuple[ActivityLogManager, AppContext]:
    context = AppContext(config=ConfigManager(), events=EventBus())
    manager = ActivityLogManager(context)
    return manager, context


def test_starts_empty_when_no_file_exists(isolated_paths):
    manager, _ = _make_manager()
    assert manager.recent() == []


def test_module_opened_event_is_logged(isolated_paths):
    manager, context = _make_manager()
    context.events.publish("module.opened", module_id="notes")

    entries = manager.recent()
    assert len(entries) == 1
    assert entries[0].event_type == "module.opened"
    assert "notes" in entries[0].summary


def test_module_opened_uses_registered_display_name(isolated_paths):
    manager, context = _make_manager()

    class _FakeModule:
        module_id = "notes"
        display_name = "Notes"

    manager.register_module_lister(lambda: [_FakeModule()])
    context.events.publish("module.opened", module_id="notes")

    assert "Notes" in manager.recent()[0].summary


def test_notification_created_event_is_logged(isolated_paths):
    manager, context = _make_manager()
    context.events.publish("notification.created", notification=_FakeNotification("Low battery", "Plug in soon."))

    entries = manager.recent()
    assert len(entries) == 1
    assert "Low battery" in entries[0].summary


def test_profile_switched_event_is_logged(isolated_paths):
    manager, context = _make_manager()
    context.events.publish("profile.switched", profile_id="abc123")

    entries = manager.recent()
    assert len(entries) == 1
    assert entries[0].event_type == "profile.switched"


def test_unrelated_events_are_not_logged(isolated_paths):
    manager, context = _make_manager()
    context.events.publish("menu.shown")
    context.events.publish("modules.rescanned", new_module_ids=[])

    assert manager.recent() == []


def test_recent_returns_most_recent_first(isolated_paths):
    manager, context = _make_manager()
    context.events.publish("module.opened", module_id="notes")
    context.events.publish("module.opened", module_id="toolbox")

    entries = manager.recent()
    assert "toolbox" in entries[0].summary
    assert "notes" in entries[1].summary


def test_recent_respects_limit(isolated_paths):
    manager, context = _make_manager()
    for i in range(5):
        context.events.publish("module.opened", module_id=f"mod{i}")

    assert len(manager.recent(limit=2)) == 2


def test_search_matches_summary_case_insensitively(isolated_paths):
    manager, context = _make_manager()
    context.events.publish("module.opened", module_id="notes")
    context.events.publish("module.opened", module_id="toolbox")

    results = manager.search("NOTES")
    assert len(results) == 1
    assert "notes" in results[0].summary


def test_search_blank_query_returns_empty(isolated_paths):
    manager, context = _make_manager()
    context.events.publish("module.opened", module_id="notes")
    assert manager.search("   ") == []


def test_entries_persist_across_a_fresh_load(isolated_paths):
    manager, context = _make_manager()
    context.events.publish("module.opened", module_id="notes")

    reloaded, _ = _make_manager()
    assert len(reloaded.recent()) == 1


def test_entries_capped_at_max(isolated_paths, monkeypatch):
    # Real _MAX_ENTRIES (5000) would work here too, but every _log() call
    # does a full-file rewrite (same pattern as every other persisted-JSON
    # manager in this codebase) — 5000+ of those in a tight test loop
    # turns a fast unit test into a ~30s one for no real coverage gain.
    # A small cap exercises the exact same capping logic.
    monkeypatch.setattr(activity_log_manager_module, "_MAX_ENTRIES", 5)
    manager, context = _make_manager()
    for i in range(15):
        context.events.publish("module.opened", module_id=f"mod{i}")

    all_entries = manager.recent(limit=100)
    assert len(all_entries) == 5
    # Oldest were dropped — the most recent one logged must still be present.
    assert "mod14" in all_entries[0].summary


def test_load_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, log_file = isolated_paths
    data_dir.mkdir(parents=True)
    log_file.write_text("{not valid json", encoding="utf-8")

    manager, _ = _make_manager()
    assert manager.recent() == []
