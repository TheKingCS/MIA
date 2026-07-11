"""
tests.test_journal_manager
=============================

Unit tests for core.journal_manager. Isolates _DATA_DIR/_ENTRIES_FILE
into a tmp_path scratch area (same monkeypatch pattern as
test_calendar_manager.py's isolated_paths).

Ordering/timestamp tests set updated_at/created_at directly on the
dataclass instances held by the manager (add_entry returns the same
object reference it stores) rather than relying on real-clock
granularity — datetime.now() is only second-precision here, so two
adds in the same test can otherwise land on an identical timestamp and
make "sorted newest first" assertions flaky.
"""

from __future__ import annotations

import pytest

import core.journal_manager as journal_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.journal_manager import JournalManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    entries_file = data_dir / "journal_entries.json"
    monkeypatch.setattr(journal_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(journal_manager_module, "_ENTRIES_FILE", entries_file)
    return data_dir, entries_file


def _make_manager() -> JournalManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return JournalManager(context)


def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.all_entries() == []


def test_add_entry_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    added = manager.add_entry(title="First Entry", body="Some text.", tags=["idea", "project-x"])

    reloaded = _make_manager()
    entries = reloaded.all_entries()
    assert len(entries) == 1
    assert entries[0].entry_id == added.entry_id
    assert entries[0].title == "First Entry"
    assert entries[0].body == "Some text."
    assert entries[0].tags == ["idea", "project-x"]
    assert entries[0].created_at
    assert entries[0].updated_at == entries[0].created_at


def test_update_entry_changes_fields_and_bumps_updated_at(isolated_paths):
    manager = _make_manager()
    entry = manager.add_entry(title="Original")
    entry.created_at = "2020-01-01T00:00:00"
    entry.updated_at = "2020-01-01T00:00:00"

    manager.update_entry(entry.entry_id, title="Renamed", body="New body.")

    assert entry.title == "Renamed"
    assert entry.body == "New body."
    assert entry.created_at == "2020-01-01T00:00:00"  # untouched
    assert entry.updated_at != "2020-01-01T00:00:00"  # bumped


def test_update_entry_rejects_protected_fields(isolated_paths):
    manager = _make_manager()
    entry = manager.add_entry(title="X")
    for protected in ("created_at", "updated_at"):
        with pytest.raises(ValueError):
            manager.update_entry(entry.entry_id, **{protected: "hacked"})


def test_update_entry_id_as_keyword_raises_type_error_at_call_site(isolated_paths):
    """entry_id is already bound positionally — passing it again via
    **fields is a plain Python TypeError, not something update_entry
    itself needs to validate."""
    manager = _make_manager()
    entry = manager.add_entry(title="X")
    with pytest.raises(TypeError):
        manager.update_entry(entry.entry_id, **{"entry_id": "hacked"})


def test_update_entry_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.update_entry("does-not-exist", title="X")


def test_update_entry_unknown_field_raises(isolated_paths):
    manager = _make_manager()
    entry = manager.add_entry(title="X")
    with pytest.raises(ValueError):
        manager.update_entry(entry.entry_id, bogus_field="X")


def test_delete_entry_removes_it_and_is_idempotent(isolated_paths):
    manager = _make_manager()
    entry = manager.add_entry(title="Gone soon")

    manager.delete_entry(entry.entry_id)
    assert manager.get_entry(entry.entry_id) is None

    manager.delete_entry(entry.entry_id)  # already gone — must not raise


def test_get_entry_returns_none_for_unknown_id(isolated_paths):
    manager = _make_manager()
    assert manager.get_entry("does-not-exist") is None


def test_all_entries_sorted_newest_updated_first(isolated_paths):
    manager = _make_manager()
    older = manager.add_entry(title="Older")
    newer = manager.add_entry(title="Newer")
    older.updated_at = "2020-01-01T00:00:00"
    newer.updated_at = "2030-01-01T00:00:00"

    ordered = manager.all_entries()
    assert [e.entry_id for e in ordered] == [newer.entry_id, older.entry_id]


def test_search_matches_title_body_and_tags_case_insensitively(isolated_paths):
    manager = _make_manager()
    by_title = manager.add_entry(title="Greenhouse Notes", body="")
    by_body = manager.add_entry(title="Untitled", body="Watered the tomatoes today.")
    by_tag = manager.add_entry(title="Random", body="", tags=["Greenhouse"])
    manager.add_entry(title="Unrelated", body="Nothing relevant here.")

    results = manager.search("greenhouse")
    result_ids = {e.entry_id for e in results}
    assert result_ids == {by_title.entry_id, by_tag.entry_id}

    tomato_results = manager.search("TOMATOES")
    assert [e.entry_id for e in tomato_results] == [by_body.entry_id]


def test_search_blank_query_returns_empty_list(isolated_paths):
    manager = _make_manager()
    manager.add_entry(title="Something")
    assert manager.search("   ") == []


def test_load_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, entries_file = isolated_paths
    data_dir.mkdir(parents=True)
    entries_file.write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()
    assert manager.all_entries() == []
