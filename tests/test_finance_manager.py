"""
tests.test_finance_manager
=============================

Unit tests for core.finance_manager. parse_snapshot_content() is
tested directly (pure, no filesystem I/O). FinanceManager itself is
tested against a real tmp_path watched folder (isolating both the
persisted-storage _DATA_DIR/_SNAPSHOTS_FILE, same monkeypatch pattern
as test_journal_manager.py's isolated_paths, and the config-driven
import folder itself via _FakeConfig, same pattern as
test_reference_library_manager.py's root_path override) — genuine
file moves/reads are exercised here since none of this needs hardware
this dev sandbox lacks, same reasoning test_script_runner.py gives for
using real subprocesses instead of mocks.
"""

from __future__ import annotations

import json

import pytest

import core.finance_manager as finance_manager_module
from core.event_bus import EventBus
from core.finance_manager import FinanceManager, FinancialSnapshot, parse_snapshot_content


class _FakeConfig:
    def __init__(self, overrides: dict) -> None:
        self._overrides = overrides

    def get(self, key: str, default=None):
        return self._overrides.get(key, default)


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    snapshots_file = data_dir / "financial_snapshots.json"
    monkeypatch.setattr(finance_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(finance_manager_module, "_SNAPSHOTS_FILE", snapshots_file)
    import_dir = tmp_path / "financial_snapshots"
    return import_dir


def _make_manager(import_dir) -> FinanceManager:
    from core.app_context import AppContext

    context = AppContext(config=_FakeConfig({"finance.snapshot_import_folder": str(import_dir)}), events=EventBus())
    return FinanceManager(context)


_VALID_SNAPSHOT = {
    "source": "real_estate_portfolio",
    "generated_at": "2026-07-16T14:32:00.000Z",
    "summary": {"total_equity": 210000},
}


# ----------------------------------------------------------------------
# parse_snapshot_content (pure)
# ----------------------------------------------------------------------

def test_parse_valid_snapshot():
    snapshot = parse_snapshot_content(json.dumps(_VALID_SNAPSHOT))
    assert snapshot.source == "real_estate_portfolio"
    assert snapshot.generated_at == "2026-07-16T14:32:00.000Z"
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
    """Real-world defensiveness: the exact Kraken export schema isn't
    confirmed, so extra/unexpected fields must not cause rejection."""
    data = dict(_VALID_SNAPSHOT)
    data["some_field_this_project_never_documented"] = {"nested": True}
    snapshot = parse_snapshot_content(json.dumps(data))
    assert snapshot is not None
    assert snapshot.data["some_field_this_project_never_documented"] == {"nested": True}


# ----------------------------------------------------------------------
# FinanceManager (real tmp_path folder, real file moves)
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
    assert newly_imported[0].source == "real_estate_portfolio"
    assert manager.latest_snapshot("real_estate_portfolio") is not None
    # Moved out of the watched folder's top level.
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
    older = dict(_VALID_SNAPSHOT, generated_at="2026-01-01T00:00:00.000Z")
    (manager.import_folder_path / "a.json").write_text(json.dumps(older), encoding="utf-8")
    manager.scan_for_new_snapshots()

    newer = dict(_VALID_SNAPSHOT, generated_at="2026-07-16T00:00:00.000Z")
    (manager.import_folder_path / "b.json").write_text(json.dumps(newer), encoding="utf-8")
    newly_imported = manager.scan_for_new_snapshots()

    assert len(newly_imported) == 1
    assert manager.latest_snapshot("real_estate_portfolio").generated_at == "2026-07-16T00:00:00.000Z"


def test_scan_discards_snapshot_older_than_stored(isolated_paths):
    manager = _make_manager(isolated_paths)
    newer = dict(_VALID_SNAPSHOT, generated_at="2026-07-16T00:00:00.000Z")
    (manager.import_folder_path / "a.json").write_text(json.dumps(newer), encoding="utf-8")
    manager.scan_for_new_snapshots()

    older = dict(_VALID_SNAPSHOT, generated_at="2026-01-01T00:00:00.000Z")
    (manager.import_folder_path / "b.json").write_text(json.dumps(older), encoding="utf-8")
    newly_imported = manager.scan_for_new_snapshots()

    assert newly_imported == []
    assert manager.latest_snapshot("real_estate_portfolio").generated_at == "2026-07-16T00:00:00.000Z"
    # Still moved out of the watched folder even though it was discarded.
    assert (manager.import_folder_path / "imported" / "b.json").exists()


def test_snapshots_persist_across_a_fresh_manager_instance(isolated_paths):
    manager = _make_manager(isolated_paths)
    (manager.import_folder_path / "export.json").write_text(json.dumps(_VALID_SNAPSHOT), encoding="utf-8")
    manager.scan_for_new_snapshots()

    second_manager = _make_manager(isolated_paths)
    assert second_manager.latest_snapshot("real_estate_portfolio").source == "real_estate_portfolio"


def test_all_latest_snapshots_returns_one_per_source(isolated_paths):
    manager = _make_manager(isolated_paths)
    (manager.import_folder_path / "a.json").write_text(json.dumps(_VALID_SNAPSHOT), encoding="utf-8")
    kraken = dict(_VALID_SNAPSHOT, source="kraken_trading_agent")
    (manager.import_folder_path / "b.json").write_text(json.dumps(kraken), encoding="utf-8")

    manager.scan_for_new_snapshots()

    sources = {s.source for s in manager.all_latest_snapshots()}
    assert sources == {"real_estate_portfolio", "kraken_trading_agent"}


def test_latest_snapshot_returns_none_for_unknown_source(isolated_paths):
    manager = _make_manager(isolated_paths)
    assert manager.latest_snapshot("nonexistent") is None
