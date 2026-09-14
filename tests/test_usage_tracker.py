"""
tests.test_usage_tracker
===========================

Unit tests for core.usage_tracker. Isolates _DATA_DIR/_USAGE_FILE into
a tmp_path scratch area (same monkeypatch pattern as
test_activity_log_manager.py's isolated_paths).
"""

from __future__ import annotations

import pytest

import core.usage_tracker as usage_tracker_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.usage_tracker import UsageTracker


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    usage_file = data_dir / "module_usage.json"
    monkeypatch.setattr(usage_tracker_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(usage_tracker_module, "_USAGE_FILE", usage_file)
    return data_dir, usage_file


def _make_tracker() -> tuple[UsageTracker, AppContext]:
    context = AppContext(config=ConfigManager(), events=EventBus())
    tracker = UsageTracker(context)
    return tracker, context


def test_starts_with_nothing_opened(isolated_paths):
    tracker, _ = _make_tracker()
    assert tracker.all_usage() == []
    assert tracker.has_been_opened("missions") is False


def test_module_opened_event_is_recorded(isolated_paths):
    tracker, context = _make_tracker()
    context.events.publish("module.opened", module_id="missions")

    assert tracker.has_been_opened("missions") is True
    usage = tracker.usage_for("missions")
    assert usage.open_count == 1
    assert usage.first_opened == usage.last_opened


def test_record_open_increments_count_and_updates_last_opened(isolated_paths):
    tracker, _ = _make_tracker()
    tracker.record_open("kitchen", when="2026-09-01T10:00:00")
    tracker.record_open("kitchen", when="2026-09-05T10:00:00")

    usage = tracker.usage_for("kitchen")
    assert usage.open_count == 2
    assert usage.first_opened == "2026-09-01T10:00:00"
    assert usage.last_opened == "2026-09-05T10:00:00"


def test_never_opened_module_ids_preserves_input_order(isolated_paths):
    tracker, _ = _make_tracker()
    tracker.record_open("kitchen")

    result = tracker.never_opened_module_ids(["missions", "kitchen", "workout"])
    assert result == ["missions", "workout"]


def test_unsuggested_never_opened_excludes_already_suggested(isolated_paths):
    tracker, _ = _make_tracker()
    tracker.mark_suggested("workout")

    result = tracker.unsuggested_never_opened_module_ids(["missions", "workout"])
    assert result == ["missions"]


def test_has_been_suggested(isolated_paths):
    tracker, _ = _make_tracker()
    assert tracker.has_been_suggested("notes") is False
    tracker.mark_suggested("notes")
    assert tracker.has_been_suggested("notes") is True


def test_usage_and_suggested_state_persist_across_a_fresh_load(isolated_paths):
    tracker, context = _make_tracker()
    tracker.record_open("kitchen", when="2026-09-01T10:00:00")
    tracker.mark_suggested("workout")

    reloaded = UsageTracker(context)
    assert reloaded.has_been_opened("kitchen") is True
    assert reloaded.usage_for("kitchen").first_opened == "2026-09-01T10:00:00"
    assert reloaded.has_been_suggested("workout") is True


def test_starts_empty_when_no_file_exists(isolated_paths):
    tracker, _ = _make_tracker()
    assert tracker.all_usage() == []
    assert tracker.has_been_suggested("missions") is False
