"""
tests.test_script_library_manager
====================================

Unit tests for core.script_library_manager. Isolates _DATA_DIR/_SCRIPTS_FILE
into a tmp_path scratch area (same monkeypatch pattern as
test_journal_manager.py's isolated_paths) — same shape throughout,
since ScriptLibraryManager is deliberately the same persisted-JSON CRUD
pattern as JournalManager, just with interpreter/category fields
instead of tags.
"""

from __future__ import annotations

import pytest

import core.script_library_manager as script_library_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.script_library_manager import ScriptLibraryManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    scripts_file = data_dir / "scripts.json"
    monkeypatch.setattr(script_library_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(script_library_manager_module, "_SCRIPTS_FILE", scripts_file)
    return data_dir, scripts_file


def _make_manager() -> ScriptLibraryManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return ScriptLibraryManager(context)


def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.all_scripts() == []


def test_add_script_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    added = manager.add_script(name="Ping Sweep", interpreter="shell", content="echo hi", category="Network")

    reloaded = _make_manager()
    scripts = reloaded.all_scripts()
    assert len(scripts) == 1
    assert scripts[0].script_id == added.script_id
    assert scripts[0].name == "Ping Sweep"
    assert scripts[0].interpreter == "shell"
    assert scripts[0].content == "echo hi"
    assert scripts[0].category == "Network"
    assert scripts[0].created_at
    assert scripts[0].updated_at == scripts[0].created_at


def test_add_script_defaults_to_shell_interpreter(isolated_paths):
    manager = _make_manager()
    added = manager.add_script(name="X")
    assert added.interpreter == "shell"


def test_add_script_rejects_unknown_interpreter_by_falling_back_to_shell(isolated_paths):
    manager = _make_manager()
    added = manager.add_script(name="X", interpreter="ruby")
    assert added.interpreter == "shell"


def test_update_script_changes_fields_and_bumps_updated_at(isolated_paths):
    manager = _make_manager()
    script = manager.add_script(name="Original", content="echo 1")
    script.created_at = "2020-01-01T00:00:00"
    script.updated_at = "2020-01-01T00:00:00"

    manager.update_script(script.script_id, name="Renamed", content="echo 2")

    assert script.name == "Renamed"
    assert script.content == "echo 2"
    assert script.created_at == "2020-01-01T00:00:00"  # untouched
    assert script.updated_at != "2020-01-01T00:00:00"  # bumped


def test_update_script_rejects_protected_fields(isolated_paths):
    manager = _make_manager()
    script = manager.add_script(name="X")
    for protected in ("created_at", "updated_at"):
        with pytest.raises(ValueError):
            manager.update_script(script.script_id, **{protected: "hacked"})


def test_update_script_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.update_script("does-not-exist", name="X")


def test_update_script_unknown_field_raises(isolated_paths):
    manager = _make_manager()
    script = manager.add_script(name="X")
    with pytest.raises(ValueError):
        manager.update_script(script.script_id, bogus_field="X")


def test_delete_script_removes_it_and_is_idempotent(isolated_paths):
    manager = _make_manager()
    script = manager.add_script(name="Gone soon")

    manager.delete_script(script.script_id)
    assert manager.get_script(script.script_id) is None

    manager.delete_script(script.script_id)  # already gone — must not raise


def test_get_script_returns_none_for_unknown_id(isolated_paths):
    manager = _make_manager()
    assert manager.get_script("does-not-exist") is None


def test_all_scripts_sorted_by_category_then_name(isolated_paths):
    manager = _make_manager()
    manager.add_script(name="Zebra", category="Network")
    manager.add_script(name="Apple", category="Network")
    manager.add_script(name="Anything", category="Automation")

    ordered = [s.name for s in manager.all_scripts()]
    assert ordered == ["Anything", "Apple", "Zebra"]


def test_search_matches_name_category_and_content_case_insensitively(isolated_paths):
    manager = _make_manager()
    by_name = manager.add_script(name="Greenhouse Monitor", content="")
    by_content = manager.add_script(name="Untitled", content="check the greenhouse sensors")
    by_category = manager.add_script(name="Random", category="Greenhouse")
    manager.add_script(name="Unrelated", content="nothing relevant here")

    results = manager.search("greenhouse")
    result_ids = {s.script_id for s in results}
    assert result_ids == {by_name.script_id, by_content.script_id, by_category.script_id}


def test_search_blank_query_returns_empty_list(isolated_paths):
    manager = _make_manager()
    manager.add_script(name="Something")
    assert manager.search("   ") == []


def test_categories_returns_distinct_sorted_nonempty_categories(isolated_paths):
    manager = _make_manager()
    manager.add_script(name="A", category="Network")
    manager.add_script(name="B", category="Automation")
    manager.add_script(name="C", category="Network")
    manager.add_script(name="D", category="")

    assert manager.categories() == ["Automation", "Network"]


def test_load_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, scripts_file = isolated_paths
    data_dir.mkdir(parents=True)
    scripts_file.write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()
    assert manager.all_scripts() == []
