"""
tests.test_calendar_manager
==============================

Unit tests for core.calendar_manager. Isolates _DATA_DIR/_EVENTS_FILE
into a tmp_path scratch area (same monkeypatch pattern as
test_backup_manager.py's isolated_paths) so these tests never touch
the real data/calendar_events.json.
"""

from __future__ import annotations

import pytest

import core.calendar_manager as calendar_manager_module
from core.app_context import AppContext
from core.calendar_manager import CalendarManager
from core.config_manager import ConfigManager
from core.event_bus import EventBus


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    events_file = data_dir / "calendar_events.json"
    monkeypatch.setattr(calendar_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(calendar_manager_module, "_EVENTS_FILE", events_file)
    return data_dir, events_file


def _make_manager() -> CalendarManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return CalendarManager(context)


def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.all_events() == []


def test_add_event_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    added = manager.add_event(title="Dentist", date="2026-08-03", time="09:30", notes="Bring insurance card.")

    reloaded = _make_manager()
    events = reloaded.all_events()
    assert len(events) == 1
    assert events[0].event_id == added.event_id
    assert events[0].title == "Dentist"
    assert events[0].date == "2026-08-03"
    assert events[0].time == "09:30"
    assert events[0].notes == "Bring insurance card."


def test_events_for_date_sorts_all_day_first_then_by_time(isolated_paths):
    manager = _make_manager()
    manager.add_event(title="Afternoon call", date="2026-08-03", time="14:00")
    manager.add_event(title="Morning standup", date="2026-08-03", time="09:00")
    manager.add_event(title="Birthday", date="2026-08-03", time=None)
    manager.add_event(title="Different day", date="2026-08-04", time="08:00")

    ordered = manager.events_for_date("2026-08-03")
    assert [e.title for e in ordered] == ["Birthday", "Morning standup", "Afternoon call"]


def test_events_for_month_groups_by_date_and_ignores_other_months(isolated_paths):
    manager = _make_manager()
    manager.add_event(title="A", date="2026-08-01", time="10:00")
    manager.add_event(title="B", date="2026-08-01", time="09:00")
    manager.add_event(title="C", date="2026-08-15")
    manager.add_event(title="D", date="2026-09-01")

    grouped = manager.events_for_month(2026, 8)
    assert set(grouped.keys()) == {"2026-08-01", "2026-08-15"}
    assert [e.title for e in grouped["2026-08-01"]] == ["B", "A"]


def test_update_event_changes_fields_and_persists(isolated_paths):
    manager = _make_manager()
    event = manager.add_event(title="Original", date="2026-08-03")

    manager.update_event(event.event_id, title="Renamed", notes="Updated notes.")

    reloaded = _make_manager()
    stored = reloaded.get_event(event.event_id)
    assert stored.title == "Renamed"
    assert stored.notes == "Updated notes."
    assert stored.date == "2026-08-03"  # untouched field is preserved


def test_update_event_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.update_event("does-not-exist", title="X")


def test_update_event_unknown_field_raises(isolated_paths):
    manager = _make_manager()
    event = manager.add_event(title="Original", date="2026-08-03")
    with pytest.raises(ValueError):
        manager.update_event(event.event_id, bogus_field="X")


def test_delete_event_removes_it_and_is_idempotent(isolated_paths):
    manager = _make_manager()
    event = manager.add_event(title="Gone soon", date="2026-08-03")

    manager.delete_event(event.event_id)
    assert manager.get_event(event.event_id) is None

    # Deleting again (already gone) must not raise.
    manager.delete_event(event.event_id)


def test_get_event_returns_none_for_unknown_id(isolated_paths):
    manager = _make_manager()
    assert manager.get_event("does-not-exist") is None


def test_load_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, events_file = isolated_paths
    data_dir.mkdir(parents=True)
    events_file.write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()
    assert manager.all_events() == []
