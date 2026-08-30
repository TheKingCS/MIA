"""
tests.test_homestead_manager
===============================

Unit tests for core.homestead_manager — mirrors
tests/test_finance_manager.py's structure exactly (same isolated
tmp_path watched folder, same _FakeConfig pattern), since
core.homestead_manager is a deliberate sibling of core.finance_manager,
not a shared abstraction (see that module's own docstring for why).
"""

from __future__ import annotations

import json

import pytest

import core.homestead_manager as homestead_manager_module
from core.event_bus import EventBus
from core.homestead_manager import HomesteadManager, parse_snapshot_content


class _FakeConfig:
    def __init__(self, overrides: dict) -> None:
        self._overrides = overrides

    def get(self, key: str, default=None):
        return self._overrides.get(key, default)


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    snapshots_file = data_dir / "homestead_snapshots.json"
    monkeypatch.setattr(homestead_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(homestead_manager_module, "_SNAPSHOTS_FILE", snapshots_file)
    import_dir = tmp_path / "homestead_snapshots"
    return import_dir


def _make_manager(import_dir) -> HomesteadManager:
    from core.app_context import AppContext

    context = AppContext(config=_FakeConfig({"homestead.snapshot_import_folder": str(import_dir)}), events=EventBus())
    return HomesteadManager(context)


_VALID_SNAPSHOT = {
    "source": "mia_homestead",
    "generated_at": "2026-08-30T22:33:19Z",
    "data": {
        "summary": {
            "critical_alert_count": 3,
            "warning_alert_count": 0,
            "yield_this_week_kg": 7.4,
            "yield_prior_week_kg": 3.9,
            "revenue_mtd": 246.0,
            "open_maintenance_critical": 1,
            "open_maintenance_total": 3,
        },
        "cells": [{"name": "Cell A", "status": "ok"}],
        "top_alert": {
            "severity": "critical",
            "source": "greenhouse_power",
            "message": "greenhouse_power: all sensors stale/invalid — freezing non-essential actuation for cell 1",
            "repeat_count": 15,
        },
    },
}


# ----------------------------------------------------------------------
# parse_snapshot_content (pure)
# ----------------------------------------------------------------------

def test_parse_valid_snapshot():
    snapshot = parse_snapshot_content(json.dumps(_VALID_SNAPSHOT))
    assert snapshot.source == "mia_homestead"
    assert snapshot.generated_at == "2026-08-30T22:33:19Z"
    assert snapshot.data == _VALID_SNAPSHOT
    assert snapshot.imported_at  # set to "now", just check it's non-empty


def test_parse_rejects_invalid_json():
    assert parse_snapshot_content("{not valid json") is None


def test_parse_rejects_non_object_json():
    assert parse_snapshot_content("[1, 2, 3]") is None


def test_parse_rejects_missing_source():
    data = dict(_VALID_SNAPSHOT)
    del data["source"]
    assert parse_snapshot_content(json.dumps(data)) is None


def test_parse_rejects_missing_generated_at():
    data = dict(_VALID_SNAPSHOT)
    del data["generated_at"]
    assert parse_snapshot_content(json.dumps(data)) is None


def test_parse_accepts_unknown_extra_fields():
    """Real-world defensiveness: mia-homestead's export shape can gain
    fields independently of this manager — extra/unexpected fields
    must not cause rejection."""
    data = dict(_VALID_SNAPSHOT)
    data["some_field_this_project_never_documented"] = {"nested": True}
    snapshot = parse_snapshot_content(json.dumps(data))
    assert snapshot is not None
    assert snapshot.data["some_field_this_project_never_documented"] == {"nested": True}


# ----------------------------------------------------------------------
# HomesteadManager (real tmp_path folder, real file moves)
# ----------------------------------------------------------------------

def test_creates_import_folder_and_subfolders(isolated_paths):
    manager = _make_manager(isolated_paths)
    assert manager.import_folder_path.is_dir()
    assert (manager.import_folder_path / "imported").is_dir()
    assert (manager.import_folder_path / "failed").is_dir()


def test_scan_with_no_files_returns_empty(isolated_paths):
    manager = _make_manager(isolated_paths)
    assert manager.scan_for_new_snapshots() == []


def test_scan_imports_a_valid_snapshot_file(isolated_paths):
    manager = _make_manager(isolated_paths)
    (manager.import_folder_path / "export.json").write_text(json.dumps(_VALID_SNAPSHOT), encoding="utf-8")

    newly_imported = manager.scan_for_new_snapshots()

    assert len(newly_imported) == 1
    assert newly_imported[0].source == "mia_homestead"
    assert manager.latest_snapshot("mia_homestead") is not None
    assert not (manager.import_folder_path / "export.json").exists()
    assert (manager.import_folder_path / "imported" / "export.json").exists()


def test_scan_moves_unparseable_file_to_failed(isolated_paths):
    manager = _make_manager(isolated_paths)
    (manager.import_folder_path / "broken.json").write_text("{not valid", encoding="utf-8")

    newly_imported = manager.scan_for_new_snapshots()

    assert newly_imported == []
    assert not (manager.import_folder_path / "broken.json").exists()
    assert (manager.import_folder_path / "failed" / "broken.json").exists()


def test_scan_does_not_reimport_already_processed_files(isolated_paths):
    manager = _make_manager(isolated_paths)
    (manager.import_folder_path / "export.json").write_text(json.dumps(_VALID_SNAPSHOT), encoding="utf-8")
    manager.scan_for_new_snapshots()

    second_scan = manager.scan_for_new_snapshots()

    assert second_scan == []


def test_scan_replaces_snapshot_with_newer_generated_at(isolated_paths):
    manager = _make_manager(isolated_paths)
    older = dict(_VALID_SNAPSHOT, generated_at="2026-08-01T00:00:00Z")
    (manager.import_folder_path / "a.json").write_text(json.dumps(older), encoding="utf-8")
    manager.scan_for_new_snapshots()

    newer = dict(_VALID_SNAPSHOT, generated_at="2026-08-30T22:33:19Z")
    (manager.import_folder_path / "b.json").write_text(json.dumps(newer), encoding="utf-8")
    newly_imported = manager.scan_for_new_snapshots()

    assert len(newly_imported) == 1
    assert manager.latest_snapshot("mia_homestead").generated_at == "2026-08-30T22:33:19Z"


def test_scan_discards_snapshot_older_than_stored(isolated_paths):
    manager = _make_manager(isolated_paths)
    newer = dict(_VALID_SNAPSHOT, generated_at="2026-08-30T22:33:19Z")
    (manager.import_folder_path / "a.json").write_text(json.dumps(newer), encoding="utf-8")
    manager.scan_for_new_snapshots()

    older = dict(_VALID_SNAPSHOT, generated_at="2026-08-01T00:00:00Z")
    (manager.import_folder_path / "b.json").write_text(json.dumps(older), encoding="utf-8")
    newly_imported = manager.scan_for_new_snapshots()

    assert newly_imported == []
    assert manager.latest_snapshot("mia_homestead").generated_at == "2026-08-30T22:33:19Z"
    assert (manager.import_folder_path / "imported" / "b.json").exists()


def test_snapshots_persist_across_a_fresh_manager_instance(isolated_paths):
    manager = _make_manager(isolated_paths)
    (manager.import_folder_path / "export.json").write_text(json.dumps(_VALID_SNAPSHOT), encoding="utf-8")
    manager.scan_for_new_snapshots()

    second_manager = _make_manager(isolated_paths)
    assert second_manager.latest_snapshot("mia_homestead").source == "mia_homestead"


def test_latest_snapshot_returns_none_for_unknown_source(isolated_paths):
    manager = _make_manager(isolated_paths)
    assert manager.latest_snapshot("nonexistent") is None
