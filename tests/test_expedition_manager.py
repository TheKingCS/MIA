"""
tests.test_expedition_manager
================================

Unit tests for core.expedition_manager. Isolates _DATA_DIR/
_EXPEDITIONS_FILE into a tmp_path scratch area (same monkeypatch pattern
as test_journal_manager.py's isolated_paths).
"""

from __future__ import annotations

import pytest

import core.expedition_manager as expedition_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.expedition_manager import ExpeditionManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    expeditions_file = data_dir / "expeditions.json"
    monkeypatch.setattr(expedition_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(expedition_manager_module, "_EXPEDITIONS_FILE", expeditions_file)
    return data_dir, expeditions_file


def _make_manager() -> ExpeditionManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return ExpeditionManager(context)


def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.all_expeditions() == []


def test_add_expedition_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    added = manager.add_expedition(
        name="Sawtooth Range Weekend",
        start_date="2026-08-14",
        end_date="2026-08-16",
        location="Sawtooth Wilderness",
        notes="Permit already booked.",
    )

    reloaded = _make_manager()
    expeditions = reloaded.all_expeditions()
    assert len(expeditions) == 1
    assert expeditions[0].expedition_id == added.expedition_id
    assert expeditions[0].name == "Sawtooth Range Weekend"
    assert expeditions[0].start_date == "2026-08-14"
    assert expeditions[0].end_date == "2026-08-16"
    assert expeditions[0].location == "Sawtooth Wilderness"
    assert expeditions[0].notes == "Permit already booked."
    assert expeditions[0].created_at
    assert expeditions[0].updated_at == expeditions[0].created_at


def test_update_expedition_changes_fields_and_bumps_updated_at(isolated_paths):
    manager = _make_manager()
    expedition = manager.add_expedition(name="Original")
    expedition.created_at = "2020-01-01T00:00:00"
    expedition.updated_at = "2020-01-01T00:00:00"

    manager.update_expedition(expedition.expedition_id, name="Renamed", location="New Area")

    assert expedition.name == "Renamed"
    assert expedition.location == "New Area"
    assert expedition.created_at == "2020-01-01T00:00:00"  # untouched
    assert expedition.updated_at != "2020-01-01T00:00:00"  # bumped


def test_update_expedition_rejects_created_at(isolated_paths):
    manager = _make_manager()
    expedition = manager.add_expedition(name="X")
    with pytest.raises(ValueError):
        manager.update_expedition(expedition.expedition_id, created_at="hacked")


def test_update_expedition_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.update_expedition("does-not-exist", name="X")


def test_update_expedition_unknown_field_raises(isolated_paths):
    manager = _make_manager()
    expedition = manager.add_expedition(name="X")
    with pytest.raises(ValueError):
        manager.update_expedition(expedition.expedition_id, bogus_field="X")


def test_delete_expedition_removes_it_and_is_idempotent(isolated_paths):
    manager = _make_manager()
    expedition = manager.add_expedition(name="Gone soon")

    manager.delete_expedition(expedition.expedition_id)
    assert manager.get_expedition(expedition.expedition_id) is None

    manager.delete_expedition(expedition.expedition_id)  # already gone — must not raise


def test_get_expedition_returns_none_for_unknown_id(isolated_paths):
    manager = _make_manager()
    assert manager.get_expedition("does-not-exist") is None


def test_all_expeditions_sorted_by_start_date(isolated_paths):
    manager = _make_manager()
    manager.add_expedition(name="Later Trip", start_date="2026-09-01")
    manager.add_expedition(name="Earlier Trip", start_date="2026-07-01")

    ordered = [e.name for e in manager.all_expeditions()]
    assert ordered == ["Earlier Trip", "Later Trip"]


def test_load_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, expeditions_file = isolated_paths
    data_dir.mkdir(parents=True)
    expeditions_file.write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()
    assert manager.all_expeditions() == []


def test_reload_picks_up_changes_written_by_another_process(isolated_paths):
    """docs/ROADMAP.md milestone v0.19 — reload() lets an auto-import's changes show up without an app restart."""
    manager = _make_manager()
    manager.add_expedition(name="Original")
    assert len(manager.all_expeditions()) == 1

    # Simulate another process (an auto-import) appending a record on disk.
    other = _make_manager()
    other.add_expedition(name="Added Elsewhere")

    assert len(manager.all_expeditions()) == 1  # stale in-memory state
    manager.reload()
    assert len(manager.all_expeditions()) == 2
