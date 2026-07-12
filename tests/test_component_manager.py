"""
tests.test_component_manager
===============================

Unit tests for core.component_manager. Isolates _DATA_DIR/_COMPONENTS_FILE
into a tmp_path scratch area (same monkeypatch pattern as
test_inventory_manager.py's isolated_paths).
"""

from __future__ import annotations

import pytest

import core.component_manager as component_manager_module
from core.app_context import AppContext
from core.component_manager import ComponentManager
from core.config_manager import ConfigManager
from core.event_bus import EventBus


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    components_file = data_dir / "components.json"
    monkeypatch.setattr(component_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(component_manager_module, "_COMPONENTS_FILE", components_file)
    return data_dir, components_file


def _make_manager() -> ComponentManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return ComponentManager(context)


def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.all_components() == []


def test_add_component_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    added = manager.add_component(
        name="10k Resistor", category="Resistor", value="10k", package="THT", quantity=50, location="Bin A3"
    )

    reloaded = _make_manager()
    components = reloaded.all_components()
    assert len(components) == 1
    assert components[0].component_id == added.component_id
    assert components[0].name == "10k Resistor"
    assert components[0].category == "Resistor"
    assert components[0].value == "10k"
    assert components[0].package == "THT"
    assert components[0].quantity == 50
    assert components[0].location == "Bin A3"
    assert components[0].updated_at


def test_add_component_clamps_negative_quantity_to_zero(isolated_paths):
    manager = _make_manager()
    added = manager.add_component(name="Widget", quantity=-5)
    assert added.quantity == 0


def test_update_component_changes_fields_and_bumps_updated_at(isolated_paths):
    manager = _make_manager()
    component = manager.add_component(name="Original", quantity=1)
    component.updated_at = "2020-01-01T00:00:00"

    manager.update_component(component.component_id, name="Renamed", quantity=5)

    assert component.name == "Renamed"
    assert component.quantity == 5
    assert component.updated_at != "2020-01-01T00:00:00"


def test_update_component_clamps_negative_quantity_to_zero(isolated_paths):
    manager = _make_manager()
    component = manager.add_component(name="Widget", quantity=5)
    manager.update_component(component.component_id, quantity=-10)
    assert component.quantity == 0


def test_update_component_rejects_updated_at(isolated_paths):
    manager = _make_manager()
    component = manager.add_component(name="X")
    with pytest.raises(ValueError):
        manager.update_component(component.component_id, updated_at="hacked")


def test_update_component_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.update_component("does-not-exist", name="X")


def test_update_component_unknown_field_raises(isolated_paths):
    manager = _make_manager()
    component = manager.add_component(name="X")
    with pytest.raises(ValueError):
        manager.update_component(component.component_id, bogus_field="X")


def test_delete_component_removes_it_and_is_idempotent(isolated_paths):
    manager = _make_manager()
    component = manager.add_component(name="Gone soon")

    manager.delete_component(component.component_id)
    assert manager.get_component(component.component_id) is None

    manager.delete_component(component.component_id)  # already gone — must not raise


def test_get_component_returns_none_for_unknown_id(isolated_paths):
    manager = _make_manager()
    assert manager.get_component("does-not-exist") is None


def test_all_components_sorted_alphabetically_by_name(isolated_paths):
    manager = _make_manager()
    manager.add_component(name="Zener Diode")
    manager.add_component(name="arduino nano")
    manager.add_component(name="Multimeter Probe")

    ordered = [c.name for c in manager.all_components()]
    assert ordered == ["arduino nano", "Multimeter Probe", "Zener Diode"]


def test_search_matches_name_category_value_package_location_and_notes(isolated_paths):
    manager = _make_manager()
    by_name = manager.add_component(name="Soldering Iron")
    by_category = manager.add_component(name="Widget", category="Capacitor")
    by_value = manager.add_component(name="Thing", value="100nF Capacitor")
    by_package = manager.add_component(name="Gadget", package="Capacitor-THT")
    by_location = manager.add_component(name="Bit", location="Capacitor Bin")
    by_notes = manager.add_component(name="Other", notes="Spare capacitor for repairs.")
    manager.add_component(name="Unrelated", category="Kitchen")

    results = manager.search("capacitor")
    result_ids = {c.component_id for c in results}
    assert result_ids == {
        by_category.component_id,
        by_value.component_id,
        by_package.component_id,
        by_location.component_id,
        by_notes.component_id,
    }

    name_results = manager.search("SOLDERING")
    assert [c.component_id for c in name_results] == [by_name.component_id]


def test_search_blank_query_returns_empty_list(isolated_paths):
    manager = _make_manager()
    manager.add_component(name="Something")
    assert manager.search("   ") == []


def test_load_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, components_file = isolated_paths
    data_dir.mkdir(parents=True)
    components_file.write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()
    assert manager.all_components() == []
