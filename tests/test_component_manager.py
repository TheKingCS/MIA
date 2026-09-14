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
import core.profile_manager as profile_manager_module
from core.app_context import AppContext
from core.component_manager import ComponentManager
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.profile_manager import ProfileManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    components_file = data_dir / "components.json"
    monkeypatch.setattr(component_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(component_manager_module, "_COMPONENTS_FILE", components_file)
    monkeypatch.setattr(component_manager_module, "_USAGE_LOG_FILE", data_dir / "component_usage_log.json")
    monkeypatch.setattr(profile_manager_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    return data_dir, components_file


def _make_manager() -> ComponentManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return ComponentManager(context)


def _make_manager_with_profile(name: str) -> tuple[ComponentManager, AppContext]:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.profiles.create_profile(name=name)
    manager = ComponentManager(context)
    return manager, context


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


# ------------------------------------------------------------------
# Multi-user pass (2026-09-14) — added_by_profile_id + the usage log.
# Third real application of the "shared object + user relationship"
# pattern (Recipes, then Inventory, now Components).
# ------------------------------------------------------------------

def test_add_component_with_no_active_profile_leaves_added_by_unset(isolated_paths):
    manager = _make_manager()
    component = manager.add_component(name="10k Resistor")
    assert component.added_by_profile_id is None


def test_add_component_attributes_to_the_real_active_profile(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    active_profile = context.profiles.get_active_profile()

    component = manager.add_component(name="10k Resistor")

    assert component.added_by_profile_id == active_profile.profile_id


def test_added_by_persists_across_a_fresh_load(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    active_profile = context.profiles.get_active_profile()
    component = manager.add_component(name="10k Resistor")

    reloaded_context = AppContext(config=ConfigManager(), events=EventBus())
    reloaded_context.profiles = context.profiles
    reloaded = ComponentManager(reloaded_context)

    assert reloaded.get_component(component.component_id).added_by_profile_id == active_profile.profile_id


def test_adjust_quantity_increments_and_decrements(isolated_paths):
    manager = _make_manager()
    component = manager.add_component(name="10k Resistor", quantity=5)

    manager.adjust_quantity(component.component_id, -1)
    assert component.quantity == 4
    manager.adjust_quantity(component.component_id, 3)
    assert component.quantity == 7


def test_adjust_quantity_clamps_at_zero(isolated_paths):
    manager = _make_manager()
    component = manager.add_component(name="10k Resistor", quantity=1)
    manager.adjust_quantity(component.component_id, -5)
    assert component.quantity == 0


def test_adjust_quantity_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.adjust_quantity("does-not-exist", 1)


def test_adjust_quantity_with_negative_delta_logs_a_real_usage_entry(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    active_profile = context.profiles.get_active_profile()
    component = manager.add_component(name="10k Resistor", quantity=5)

    manager.adjust_quantity(component.component_id, -1)

    log = manager.usage_log_for_component(component.component_id)
    assert len(log) == 1
    assert log[0].delta == -1
    assert log[0].profile_id == active_profile.profile_id


def test_adjust_quantity_with_zero_delta_logs_nothing(isolated_paths):
    manager = _make_manager()
    component = manager.add_component(name="10k Resistor")
    manager.adjust_quantity(component.component_id, 0)
    assert manager.usage_log_for_component(component.component_id) == []


def test_adjust_quantity_logs_the_full_attempted_delta_even_when_clamped(isolated_paths):
    manager = _make_manager()
    component = manager.add_component(name="10k Resistor", quantity=0)
    manager.adjust_quantity(component.component_id, -1)
    assert component.quantity == 0
    log = manager.usage_log_for_component(component.component_id)
    assert len(log) == 1
    assert log[0].delta == -1


def test_times_used_counts_only_negative_deltas(isolated_paths):
    manager = _make_manager()
    component = manager.add_component(name="10k Resistor", quantity=5)
    manager.adjust_quantity(component.component_id, -1)
    manager.adjust_quantity(component.component_id, -1)
    manager.adjust_quantity(component.component_id, 2)  # a restock, not a "use"
    assert manager.times_used(component.component_id) == 2


def test_times_used_household_total_includes_every_profile(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    second_profile = context.profiles.create_profile(name="Faith", make_active=False)
    component = manager.add_component(name="10k Resistor", quantity=5)

    manager.adjust_quantity(component.component_id, -1)  # Alex (active)
    context.profiles.set_active_profile(second_profile.profile_id)
    manager.adjust_quantity(component.component_id, -1)  # Faith

    assert manager.times_used(component.component_id) == 2


def test_times_used_scoped_to_one_profile_excludes_the_others(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    alex = context.profiles.get_active_profile()
    faith = context.profiles.create_profile(name="Faith", make_active=False)
    component = manager.add_component(name="10k Resistor", quantity=5)

    manager.adjust_quantity(component.component_id, -1)  # Alex
    context.profiles.set_active_profile(faith.profile_id)
    manager.adjust_quantity(component.component_id, -1)  # Faith

    assert manager.times_used(component.component_id, profile_id=alex.profile_id) == 1
    assert manager.times_used(component.component_id, profile_id=faith.profile_id) == 1


def test_last_used_returns_the_most_recent_real_consumption_event(isolated_paths):
    manager = _make_manager()
    component = manager.add_component(name="10k Resistor", quantity=5)
    manager.adjust_quantity(component.component_id, -1)
    latest = manager.adjust_quantity(component.component_id, -1)

    result = manager.last_used(component.component_id)
    assert result is not None
    assert result.timestamp == latest.updated_at


def test_last_used_ignores_restocks(isolated_paths):
    manager = _make_manager()
    component = manager.add_component(name="10k Resistor", quantity=5)
    manager.adjust_quantity(component.component_id, 10)  # a restock, not a use
    assert manager.last_used(component.component_id) is None


def test_last_used_none_when_never_used(isolated_paths):
    manager = _make_manager()
    component = manager.add_component(name="10k Resistor")
    assert manager.last_used(component.component_id) is None


def test_last_used_picks_the_truly_last_entry_even_with_identical_timestamps(isolated_paths):
    """Same real regression class caught in core.inventory_manager's
    own last_used() (2026-09-14) — several quick adjustments can share
    a one-second-resolution timestamp; the fix here was applied from
    the start rather than repeating that bug."""
    manager = _make_manager()
    component = manager.add_component(name="10k Resistor", quantity=5)
    from core.component_manager import ComponentUsageEntry

    same_moment = "2026-09-14T12:00:00"
    manager._usage_log.append(ComponentUsageEntry(entry_id="e1", component_id=component.component_id, delta=-1, profile_id="alex", timestamp=same_moment))
    manager._usage_log.append(ComponentUsageEntry(entry_id="e2", component_id=component.component_id, delta=-1, profile_id="faith", timestamp=same_moment))

    result = manager.last_used(component.component_id)
    assert result is not None
    assert result.profile_id == "faith"


def test_usage_log_isolated_per_component(isolated_paths):
    manager = _make_manager()
    component_a = manager.add_component(name="10k Resistor", quantity=5)
    component_b = manager.add_component(name="100nF Capacitor", quantity=3)

    manager.adjust_quantity(component_a.component_id, -1)
    manager.adjust_quantity(component_b.component_id, -1)
    manager.adjust_quantity(component_b.component_id, -1)

    assert len(manager.usage_log_for_component(component_a.component_id)) == 1
    assert len(manager.usage_log_for_component(component_b.component_id)) == 2


def test_usage_log_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    component = manager.add_component(name="10k Resistor", quantity=5)
    manager.adjust_quantity(component.component_id, -1)

    reloaded = _make_manager()
    assert len(reloaded.usage_log_for_component(component.component_id)) == 1


def test_load_usage_log_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, _ = isolated_paths
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "component_usage_log.json").write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()  # must not raise
    assert manager.usage_log_for_component("anything") == []
