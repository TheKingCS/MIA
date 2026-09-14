"""
tests.test_inventory_manager
===============================

Unit tests for core.inventory_manager. Isolates _DATA_DIR/_ITEMS_FILE
into a tmp_path scratch area (same monkeypatch pattern as
test_calendar_manager.py's isolated_paths).
"""

from __future__ import annotations

import pytest

import core.inventory_manager as inventory_manager_module
import core.profile_manager as profile_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.inventory_manager import InventoryManager
from core.profile_manager import ProfileManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    items_file = data_dir / "inventory_items.json"
    monkeypatch.setattr(inventory_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(inventory_manager_module, "_ITEMS_FILE", items_file)
    monkeypatch.setattr(inventory_manager_module, "_USAGE_LOG_FILE", data_dir / "inventory_usage_log.json")
    monkeypatch.setattr(profile_manager_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    return data_dir, items_file


def _make_manager() -> InventoryManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return InventoryManager(context)


def _make_manager_with_profile(name: str) -> tuple[InventoryManager, AppContext]:
    """Same as _make_manager() but with a real active profile wired,
    for tests that need real profile attribution."""
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.profiles.create_profile(name=name)
    manager = InventoryManager(context)
    return manager, context


def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.all_items() == []


def test_add_item_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    added = manager.add_item(name="Duct Tape", quantity=3, category="Tools", location="Shelf A")

    reloaded = _make_manager()
    items = reloaded.all_items()
    assert len(items) == 1
    assert items[0].item_id == added.item_id
    assert items[0].name == "Duct Tape"
    assert items[0].quantity == 3
    assert items[0].category == "Tools"
    assert items[0].location == "Shelf A"
    assert items[0].updated_at


def test_add_item_clamps_negative_quantity_to_zero(isolated_paths):
    manager = _make_manager()
    added = manager.add_item(name="Widget", quantity=-5)
    assert added.quantity == 0


def test_update_item_changes_fields_and_bumps_updated_at(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Original", quantity=1)
    item.updated_at = "2020-01-01T00:00:00"

    manager.update_item(item.item_id, name="Renamed", quantity=5)

    assert item.name == "Renamed"
    assert item.quantity == 5
    assert item.updated_at != "2020-01-01T00:00:00"


def test_update_item_clamps_negative_quantity_to_zero(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Widget", quantity=5)
    manager.update_item(item.item_id, quantity=-10)
    assert item.quantity == 0


def test_update_item_rejects_updated_at(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="X")
    with pytest.raises(ValueError):
        manager.update_item(item.item_id, updated_at="hacked")


def test_update_item_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.update_item("does-not-exist", name="X")


def test_update_item_unknown_field_raises(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="X")
    with pytest.raises(ValueError):
        manager.update_item(item.item_id, bogus_field="X")


def test_adjust_quantity_increments_and_decrements(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Widget", quantity=5)

    manager.adjust_quantity(item.item_id, 1)
    assert item.quantity == 6

    manager.adjust_quantity(item.item_id, -2)
    assert item.quantity == 4


def test_adjust_quantity_clamps_at_zero(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Widget", quantity=1)
    manager.adjust_quantity(item.item_id, -5)
    assert item.quantity == 0


def test_adjust_quantity_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.adjust_quantity("does-not-exist", 1)


def test_delete_item_removes_it_and_is_idempotent(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Gone soon")

    manager.delete_item(item.item_id)
    assert manager.get_item(item.item_id) is None

    manager.delete_item(item.item_id)  # already gone — must not raise


def test_get_item_returns_none_for_unknown_id(isolated_paths):
    manager = _make_manager()
    assert manager.get_item("does-not-exist") is None


def test_all_items_sorted_alphabetically_by_name(isolated_paths):
    manager = _make_manager()
    manager.add_item(name="Zebra Clamp")
    manager.add_item(name="apple crate")
    manager.add_item(name="Multimeter")

    ordered = [i.name for i in manager.all_items()]
    assert ordered == ["apple crate", "Multimeter", "Zebra Clamp"]


def test_search_matches_name_category_location_and_notes(isolated_paths):
    manager = _make_manager()
    by_name = manager.add_item(name="Soldering Iron")
    by_category = manager.add_item(name="Widget", category="Electronics")
    by_location = manager.add_item(name="Gadget", location="Electronics Bin")
    by_notes = manager.add_item(name="Thing", notes="Used for electronics repair.")
    manager.add_item(name="Unrelated", category="Kitchen")

    results = manager.search("electronics")
    result_ids = {i.item_id for i in results}
    assert result_ids == {by_category.item_id, by_location.item_id, by_notes.item_id}

    name_results = manager.search("SOLDERING")
    assert [i.item_id for i in name_results] == [by_name.item_id]


def test_search_blank_query_returns_empty_list(isolated_paths):
    manager = _make_manager()
    manager.add_item(name="Something")
    assert manager.search("   ") == []


def test_load_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, items_file = isolated_paths
    data_dir.mkdir(parents=True)
    items_file.write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()
    assert manager.all_items() == []


def test_reload_picks_up_changes_written_by_another_process(isolated_paths):
    """docs/ROADMAP.md milestone v0.19 — reload() lets an auto-import's changes show up without an app restart."""
    manager = _make_manager()
    manager.add_item(name="Original")
    assert len(manager.all_items()) == 1

    other = _make_manager()
    other.add_item(name="Added Elsewhere")

    assert len(manager.all_items()) == 1  # stale in-memory state
    manager.reload()
    assert len(manager.all_items()) == 2


# ------------------------------------------------------------------
# Multi-user pass (2026-09-14) — added_by_profile_id + the usage log.
# Same "shared object + user relationship" pattern as
# core.kitchen_manager.Recipe/MealLogEntry, applied to Inventory.
# ------------------------------------------------------------------

def test_add_item_with_no_active_profile_leaves_added_by_unset(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Paper Towels")
    assert item.added_by_profile_id is None


def test_add_item_attributes_to_the_real_active_profile(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    active_profile = context.profiles.get_active_profile()

    item = manager.add_item(name="Paper Towels")

    assert item.added_by_profile_id == active_profile.profile_id


def test_added_by_persists_across_a_fresh_load(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    active_profile = context.profiles.get_active_profile()
    item = manager.add_item(name="Paper Towels")

    reloaded_context = AppContext(config=ConfigManager(), events=EventBus())
    reloaded_context.profiles = context.profiles
    reloaded = InventoryManager(reloaded_context)

    assert reloaded.get_item(item.item_id).added_by_profile_id == active_profile.profile_id


def test_adjust_quantity_with_negative_delta_logs_a_real_usage_entry(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    active_profile = context.profiles.get_active_profile()
    item = manager.add_item(name="Paper Towels", quantity=5)

    manager.adjust_quantity(item.item_id, -1)

    log = manager.usage_log_for_item(item.item_id)
    assert len(log) == 1
    assert log[0].delta == -1
    assert log[0].profile_id == active_profile.profile_id


def test_adjust_quantity_with_positive_delta_also_logs_an_entry(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Paper Towels")

    manager.adjust_quantity(item.item_id, 3)

    assert len(manager.usage_log_for_item(item.item_id)) == 1
    assert manager.usage_log_for_item(item.item_id)[0].delta == 3


def test_adjust_quantity_with_zero_delta_logs_nothing(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Paper Towels")

    manager.adjust_quantity(item.item_id, 0)

    assert manager.usage_log_for_item(item.item_id) == []


def test_adjust_quantity_logs_the_full_attempted_delta_even_when_clamped(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Paper Towels", quantity=0)

    manager.adjust_quantity(item.item_id, -1)  # clamps to 0, but is still a real "tried to use it" event

    assert item.quantity == 0
    log = manager.usage_log_for_item(item.item_id)
    assert len(log) == 1
    assert log[0].delta == -1


def test_times_used_counts_only_negative_deltas(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Paper Towels", quantity=5)
    manager.adjust_quantity(item.item_id, -1)
    manager.adjust_quantity(item.item_id, -1)
    manager.adjust_quantity(item.item_id, 2)  # a restock, not a "use"

    assert manager.times_used(item.item_id) == 2


def test_times_used_household_total_includes_every_profile(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    second_profile = context.profiles.create_profile(name="Faith", make_active=False)
    item = manager.add_item(name="Paper Towels", quantity=5)

    manager.adjust_quantity(item.item_id, -1)  # Alex (active)
    context.profiles.set_active_profile(second_profile.profile_id)
    manager.adjust_quantity(item.item_id, -1)  # Faith

    assert manager.times_used(item.item_id) == 2


def test_times_used_scoped_to_one_profile_excludes_the_others(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    alex = context.profiles.get_active_profile()
    faith = context.profiles.create_profile(name="Faith", make_active=False)
    item = manager.add_item(name="Paper Towels", quantity=5)

    manager.adjust_quantity(item.item_id, -1)  # Alex
    context.profiles.set_active_profile(faith.profile_id)
    manager.adjust_quantity(item.item_id, -1)  # Faith

    assert manager.times_used(item.item_id, profile_id=alex.profile_id) == 1
    assert manager.times_used(item.item_id, profile_id=faith.profile_id) == 1


def test_times_used_scoped_to_a_profile_still_counts_unattributed_entries(isolated_paths):
    """Same real-world case core.kitchen_manager.times_made() already
    handles: usage logged with no active profile is a real household
    event, not nobody's — it should still count toward any one
    person's own view, same as an unattributed Mission counts toward
    everyone's missions_completed."""
    manager, context = _make_manager_with_profile("Alex")
    alex = context.profiles.get_active_profile()
    item = manager.add_item(name="Paper Towels", quantity=5)

    context.profiles = None  # simulate no active profile for this one adjustment
    manager.adjust_quantity(item.item_id, -1)

    assert manager.times_used(item.item_id, profile_id=alex.profile_id) == 1


def test_last_used_returns_the_most_recent_real_consumption_event(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Paper Towels", quantity=5)
    manager.adjust_quantity(item.item_id, -1)
    latest = manager.adjust_quantity(item.item_id, -1)

    result = manager.last_used(item.item_id)
    assert result is not None
    assert result.timestamp == latest.updated_at


def test_last_used_ignores_restocks(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Paper Towels", quantity=5)
    manager.adjust_quantity(item.item_id, 10)  # a restock, not a use

    assert manager.last_used(item.item_id) is None


def test_last_used_none_when_never_used(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Paper Towels")
    assert manager.last_used(item.item_id) is None


def test_last_used_picks_the_truly_last_entry_even_with_identical_timestamps(isolated_paths):
    """Real regression, caught via an actual manual verification
    screenshot (2026-09-14): several quick adjustments can land in the
    same one-second-resolution timestamp. last_used() must return the
    entry that was actually appended last (real append order), not
    whichever one a naive max()-by-timestamp tie-break happens to pick
    first. Exercised directly against the usage log rather than
    freezing the clock — the two entries below share one real
    timestamp on purpose."""
    manager = _make_manager()
    item = manager.add_item(name="Paper Towels", quantity=5)
    from core.inventory_manager import InventoryUsageEntry

    same_moment = "2026-09-14T12:00:00"
    manager._usage_log.append(InventoryUsageEntry(entry_id="e1", item_id=item.item_id, delta=-1, profile_id="alex", timestamp=same_moment))
    manager._usage_log.append(InventoryUsageEntry(entry_id="e2", item_id=item.item_id, delta=-1, profile_id="faith", timestamp=same_moment))

    result = manager.last_used(item.item_id)
    assert result is not None
    assert result.profile_id == "faith"  # the truly last one appended, not the first tied entry


def test_usage_log_isolated_per_item(isolated_paths):
    manager = _make_manager()
    item_a = manager.add_item(name="Paper Towels", quantity=5)
    item_b = manager.add_item(name="Dish Soap", quantity=3)

    manager.adjust_quantity(item_a.item_id, -1)
    manager.adjust_quantity(item_b.item_id, -1)
    manager.adjust_quantity(item_b.item_id, -1)

    assert len(manager.usage_log_for_item(item_a.item_id)) == 1
    assert len(manager.usage_log_for_item(item_b.item_id)) == 2


def test_usage_log_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Paper Towels", quantity=5)
    manager.adjust_quantity(item.item_id, -1)

    reloaded = _make_manager()
    assert len(reloaded.usage_log_for_item(item.item_id)) == 1


def test_load_usage_log_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, _ = isolated_paths
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "inventory_usage_log.json").write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()  # must not raise
    assert manager.usage_log_for_item("anything") == []
