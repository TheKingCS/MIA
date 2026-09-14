"""
tests.test_material_manager
==============================

Unit tests for core.material_manager. Isolates _DATA_DIR/_MATERIALS_FILE
into a tmp_path scratch area, same monkeypatch pattern as
test_component_manager.py's isolated_paths. materials_needing_restock()
is also tested directly as a pure function (no filesystem I/O), same
reasoning as every other pure-formatting/pure-logic function in this
project's test suite.
"""

from __future__ import annotations

import pytest

import core.material_manager as material_manager_module
import core.profile_manager as profile_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.material_manager import Material, MaterialManager, materials_needing_restock
from core.profile_manager import ProfileManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    materials_file = data_dir / "materials.json"
    monkeypatch.setattr(material_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(material_manager_module, "_MATERIALS_FILE", materials_file)
    monkeypatch.setattr(material_manager_module, "_USAGE_LOG_FILE", data_dir / "material_usage_log.json")
    monkeypatch.setattr(profile_manager_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    return data_dir, materials_file


def _make_manager() -> MaterialManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return MaterialManager(context)


def _make_manager_with_profile(name: str) -> tuple[MaterialManager, AppContext]:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.profiles.create_profile(name=name)
    manager = MaterialManager(context)
    return manager, context


# ----------------------------------------------------------------------
# materials_needing_restock (pure)
# ----------------------------------------------------------------------

def test_restock_check_flags_at_or_below_threshold():
    low = Material(material_id="a", name="Plywood", quantity_on_hand=2, reorder_threshold=5)
    at_threshold = Material(material_id="b", name="Filament", quantity_on_hand=5, reorder_threshold=5)
    plenty = Material(material_id="c", name="Screws", quantity_on_hand=500, reorder_threshold=50)

    flagged = materials_needing_restock([low, at_threshold, plenty])

    assert {m.material_id for m in flagged} == {"a", "b"}


def test_restock_check_empty_list_returns_empty():
    assert materials_needing_restock([]) == []


# ----------------------------------------------------------------------
# MaterialManager (real tmp_path persistence)
# ----------------------------------------------------------------------

def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.all_materials() == []


def test_add_material_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    added = manager.add_material(
        name="Baltic Birch Plywood", unit="sheet", unit_cost=45.0, quantity_on_hand=12,
        reorder_threshold=3, supplier="Acme Lumber", location="Rack B",
    )

    reloaded = _make_manager()
    materials = reloaded.all_materials()
    assert len(materials) == 1
    assert materials[0].material_id == added.material_id
    assert materials[0].name == "Baltic Birch Plywood"
    assert materials[0].unit == "sheet"
    assert materials[0].unit_cost == 45.0
    assert materials[0].quantity_on_hand == 12
    assert materials[0].reorder_threshold == 3
    assert materials[0].supplier == "Acme Lumber"
    assert materials[0].location == "Rack B"
    assert materials[0].updated_at


def test_add_material_clamps_negative_values_to_zero(isolated_paths):
    manager = _make_manager()
    added = manager.add_material(name="Widget", unit_cost=-5, quantity_on_hand=-10, reorder_threshold=-1)
    assert added.unit_cost == 0
    assert added.quantity_on_hand == 0
    assert added.reorder_threshold == 0


def test_update_material_changes_fields_and_bumps_updated_at(isolated_paths):
    manager = _make_manager()
    material = manager.add_material(name="Original", quantity_on_hand=1)
    material.updated_at = "2020-01-01T00:00:00"

    manager.update_material(material.material_id, name="Renamed", quantity_on_hand=5)

    assert material.name == "Renamed"
    assert material.quantity_on_hand == 5
    assert material.updated_at != "2020-01-01T00:00:00"


def test_update_material_clamps_negative_quantity_to_zero(isolated_paths):
    manager = _make_manager()
    material = manager.add_material(name="Widget", quantity_on_hand=5)
    manager.update_material(material.material_id, quantity_on_hand=-10)
    assert material.quantity_on_hand == 0


def test_update_material_rejects_updated_at(isolated_paths):
    manager = _make_manager()
    material = manager.add_material(name="X")
    with pytest.raises(ValueError):
        manager.update_material(material.material_id, updated_at="hacked")


def test_update_material_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.update_material("does-not-exist", name="X")


def test_update_material_unknown_field_raises(isolated_paths):
    manager = _make_manager()
    material = manager.add_material(name="X")
    with pytest.raises(ValueError):
        manager.update_material(material.material_id, bogus_field="X")


def test_delete_material_removes_it_and_is_idempotent(isolated_paths):
    manager = _make_manager()
    material = manager.add_material(name="Gone soon")

    manager.delete_material(material.material_id)
    assert manager.get_material(material.material_id) is None

    manager.delete_material(material.material_id)  # already gone — must not raise


def test_get_material_returns_none_for_unknown_id(isolated_paths):
    manager = _make_manager()
    assert manager.get_material("does-not-exist") is None


def test_all_materials_sorted_alphabetically_by_name(isolated_paths):
    manager = _make_manager()
    manager.add_material(name="Zinc Sheet")
    manager.add_material(name="acrylic sheet")
    manager.add_material(name="Maple Dowels")

    ordered = [m.name for m in manager.all_materials()]
    assert ordered == ["acrylic sheet", "Maple Dowels", "Zinc Sheet"]


def test_search_matches_name_supplier_location_and_notes(isolated_paths):
    manager = _make_manager()
    by_name = manager.add_material(name="Baltic Birch")
    by_supplier = manager.add_material(name="Widget", supplier="Baltic Supply Co")
    by_location = manager.add_material(name="Thing", location="Baltic Rack")
    by_notes = manager.add_material(name="Gadget", notes="Sourced from Baltic region.")
    manager.add_material(name="Unrelated", supplier="Acme")

    results = manager.search("baltic")
    result_ids = {m.material_id for m in results}
    assert result_ids == {by_supplier.material_id, by_location.material_id, by_notes.material_id, by_name.material_id}

    name_results = manager.search("GADGET")
    assert [m.material_id for m in name_results] == [by_notes.material_id]


def test_search_blank_query_returns_empty_list(isolated_paths):
    manager = _make_manager()
    manager.add_material(name="Something")
    assert manager.search("   ") == []


def test_load_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, materials_file = isolated_paths
    data_dir.mkdir(parents=True)
    materials_file.write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()
    assert manager.all_materials() == []


def test_manager_materials_needing_restock_reflects_live_data(isolated_paths):
    manager = _make_manager()
    manager.add_material(name="Low Stock Item", quantity_on_hand=1, reorder_threshold=5)
    manager.add_material(name="Well Stocked Item", quantity_on_hand=100, reorder_threshold=5)

    flagged = manager.materials_needing_restock()

    assert [m.name for m in flagged] == ["Low Stock Item"]


# ------------------------------------------------------------------
# Multi-user pass (2026-09-14) — added_by_profile_id + the usage log.
# Fourth real application of the "shared object + user relationship"
# pattern (Recipes, Inventory, Component DB, now Materials). `delta`
# is a real float here, matching this domain's own continuous units.
# ------------------------------------------------------------------

def test_add_material_with_no_active_profile_leaves_added_by_unset(isolated_paths):
    manager = _make_manager()
    material = manager.add_material(name="Plywood")
    assert material.added_by_profile_id is None


def test_add_material_attributes_to_the_real_active_profile(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    active_profile = context.profiles.get_active_profile()

    material = manager.add_material(name="Plywood")

    assert material.added_by_profile_id == active_profile.profile_id


def test_added_by_persists_across_a_fresh_load(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    active_profile = context.profiles.get_active_profile()
    material = manager.add_material(name="Plywood")

    reloaded_context = AppContext(config=ConfigManager(), events=EventBus())
    reloaded_context.profiles = context.profiles
    reloaded = MaterialManager(reloaded_context)

    assert reloaded.get_material(material.material_id).added_by_profile_id == active_profile.profile_id


def test_adjust_quantity_increments_and_decrements_with_float_deltas(isolated_paths):
    manager = _make_manager()
    material = manager.add_material(name="Plywood", quantity_on_hand=10.0)

    manager.adjust_quantity(material.material_id, -2.5)
    assert material.quantity_on_hand == 7.5
    manager.adjust_quantity(material.material_id, 1.25)
    assert material.quantity_on_hand == 8.75


def test_adjust_quantity_clamps_at_zero(isolated_paths):
    manager = _make_manager()
    material = manager.add_material(name="Plywood", quantity_on_hand=1.0)
    manager.adjust_quantity(material.material_id, -5.0)
    assert material.quantity_on_hand == 0.0


def test_adjust_quantity_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.adjust_quantity("does-not-exist", 1.0)


def test_adjust_quantity_with_negative_delta_logs_a_real_usage_entry(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    active_profile = context.profiles.get_active_profile()
    material = manager.add_material(name="Plywood", quantity_on_hand=10.0)

    manager.adjust_quantity(material.material_id, -2.5)

    log = manager.usage_log_for_material(material.material_id)
    assert len(log) == 1
    assert log[0].delta == -2.5
    assert log[0].profile_id == active_profile.profile_id


def test_adjust_quantity_with_zero_delta_logs_nothing(isolated_paths):
    manager = _make_manager()
    material = manager.add_material(name="Plywood")
    manager.adjust_quantity(material.material_id, 0)
    assert manager.usage_log_for_material(material.material_id) == []


def test_times_used_counts_only_negative_deltas(isolated_paths):
    manager = _make_manager()
    material = manager.add_material(name="Plywood", quantity_on_hand=10.0)
    manager.adjust_quantity(material.material_id, -1.0)
    manager.adjust_quantity(material.material_id, -1.0)
    manager.adjust_quantity(material.material_id, 5.0)  # a restock, not a "use"
    assert manager.times_used(material.material_id) == 2


def test_times_used_household_total_includes_every_profile(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    second_profile = context.profiles.create_profile(name="Faith", make_active=False)
    material = manager.add_material(name="Plywood", quantity_on_hand=10.0)

    manager.adjust_quantity(material.material_id, -1.0)  # Alex (active)
    context.profiles.set_active_profile(second_profile.profile_id)
    manager.adjust_quantity(material.material_id, -1.0)  # Faith

    assert manager.times_used(material.material_id) == 2


def test_times_used_scoped_to_one_profile_excludes_the_others(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    alex = context.profiles.get_active_profile()
    faith = context.profiles.create_profile(name="Faith", make_active=False)
    material = manager.add_material(name="Plywood", quantity_on_hand=10.0)

    manager.adjust_quantity(material.material_id, -1.0)  # Alex
    context.profiles.set_active_profile(faith.profile_id)
    manager.adjust_quantity(material.material_id, -1.0)  # Faith

    assert manager.times_used(material.material_id, profile_id=alex.profile_id) == 1
    assert manager.times_used(material.material_id, profile_id=faith.profile_id) == 1


def test_last_used_returns_the_most_recent_real_consumption_event(isolated_paths):
    manager = _make_manager()
    material = manager.add_material(name="Plywood", quantity_on_hand=10.0)
    manager.adjust_quantity(material.material_id, -1.0)
    latest = manager.adjust_quantity(material.material_id, -1.0)

    result = manager.last_used(material.material_id)
    assert result is not None
    assert result.timestamp == latest.updated_at


def test_last_used_ignores_restocks(isolated_paths):
    manager = _make_manager()
    material = manager.add_material(name="Plywood", quantity_on_hand=10.0)
    manager.adjust_quantity(material.material_id, 10.0)  # a restock, not a use
    assert manager.last_used(material.material_id) is None


def test_last_used_none_when_never_used(isolated_paths):
    manager = _make_manager()
    material = manager.add_material(name="Plywood")
    assert manager.last_used(material.material_id) is None


def test_last_used_picks_the_truly_last_entry_even_with_identical_timestamps(isolated_paths):
    manager = _make_manager()
    material = manager.add_material(name="Plywood", quantity_on_hand=10.0)
    from core.material_manager import MaterialUsageEntry

    same_moment = "2026-09-14T12:00:00"
    manager._usage_log.append(MaterialUsageEntry(entry_id="e1", material_id=material.material_id, delta=-1.0, profile_id="alex", timestamp=same_moment))
    manager._usage_log.append(MaterialUsageEntry(entry_id="e2", material_id=material.material_id, delta=-1.0, profile_id="faith", timestamp=same_moment))

    result = manager.last_used(material.material_id)
    assert result is not None
    assert result.profile_id == "faith"


def test_usage_log_isolated_per_material(isolated_paths):
    manager = _make_manager()
    material_a = manager.add_material(name="Plywood", quantity_on_hand=10.0)
    material_b = manager.add_material(name="Filament", quantity_on_hand=5.0)

    manager.adjust_quantity(material_a.material_id, -1.0)
    manager.adjust_quantity(material_b.material_id, -1.0)
    manager.adjust_quantity(material_b.material_id, -1.0)

    assert len(manager.usage_log_for_material(material_a.material_id)) == 1
    assert len(manager.usage_log_for_material(material_b.material_id)) == 2


def test_usage_log_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    material = manager.add_material(name="Plywood", quantity_on_hand=10.0)
    manager.adjust_quantity(material.material_id, -1.0)

    reloaded = _make_manager()
    assert len(reloaded.usage_log_for_material(material.material_id)) == 1


def test_load_usage_log_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, _ = isolated_paths
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "material_usage_log.json").write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()  # must not raise
    assert manager.usage_log_for_material("anything") == []
